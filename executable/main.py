"""
main.py — Entry point for the ApenasPromo executable.

Boot sequence:
1. Check config.json (license key + machine_id)
2. Validate license against remote API
3. Check for updates
4. Load remote config
5. Start BotRunner
6. Start Flask web server on 127.0.0.1:8080
7. Open browser
8. Start heartbeat daemon
9. Keep process alive
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import subprocess
import requests
import webbrowser
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

# ── Constants ──────────────────────────────────────────────────────────────────
VERSION = "1.0.0"
API_BASE: str = ""  # Will be set from .env at boot time

CONFIG_PATH = Path("config.json")
LOCAL_PORT = 8080
MAX_LOGS = 200



# ── In-memory log store ────────────────────────────────────────────────────────
_logs: deque[dict] = deque(maxlen=MAX_LOGS)
_lock = threading.Lock()


def add_log(nivel: str, mensagem: str) -> None:
    entry = {
        "nivel": nivel,
        "mensagem": mensagem,
        "horario": datetime.now(timezone.utc).strftime("%H:%M:%S"),
    }
    with _lock:
        _logs.append(entry)


# ── Load local .env fallback ──────────────────────────────────────────────────
def _load_env_fallback() -> dict:
    """
    When the VPS API is not configured, read credentials directly from
    the .env file (or environment variables) for local single-user mode.
    """
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env", override=False)
    
    env_local = Path(".env.local")
    if env_local.exists():
        load_dotenv(dotenv_path=".env.local", override=True)
    return {
        "api_id": os.getenv("API_ID", ""),
        "api_hash": os.getenv("API_HASH", ""),
        "phone": os.getenv("TELEGRAM_PHONE", ""),
        "sources": [s for s in os.getenv("SOURCE", "").split(",") if s],
        "destination_telegram": os.getenv("DESTINATION", ""),
        "delay_segundos": int(os.getenv("DELAY", "3")),
        "wpp_destinations": [s for s in os.getenv("WHATSAPP_DESTINATIONS", "").split(",") if s],
        "whatsapp_endpoint": os.getenv("WHATSAPP_ENDPOINT", "http://localhost:4000/send"),
        "send_telegram": os.getenv("ENABLE_TELEGRAM", "true").lower() == "true",
        "send_whatsapp": os.getenv("ENABLE_WHATSAPP", "true").lower() == "true",
        "conv_shopee": os.getenv("CONV_SHOPEE", "true").lower() == "true",
        "conv_ali": os.getenv("CONV_ALI", "true").lower() == "true",
        "conv_ml": os.getenv("CONV_ML", "true").lower() == "true",
        "filtros": {},
        "shopee_token": os.getenv("SHOPEE_TOKEN", ""),
        "ali_key": os.getenv("ALIEXPRESS_APP_KEY", ""),
        "ali_secret": os.getenv("ALIEXPRESS_APP_SECRET", ""),
        "ali_tracking": os.getenv("ALIEXPRESS_TRACKING_ID", ""),
        "ml_token": os.getenv("ML_TOKEN", ""),
        "session_string": os.getenv("TELEGRAM_SESSION_STRING", ""),
    }


def _boot():
    # ── Load .env BEFORE any imports that read environment variables ──────────
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env", override=True)
    env_local = Path(".env.local")
    if env_local.exists():
        load_dotenv(dotenv_path=".env.local", override=True)

    global API_BASE
    API_BASE = os.environ.get("APRO_API_BASE", "")

    # Optional imports — only available if API is configured
    license_key: str = ""

    machine_id: str = ""
    license_info: dict = {}
    remote_cfg: dict = {}
    config_error: str = ""
    lic_module = None
    config_loader = None

    # ── Try to import license/config modules ──────────────────────────────────
    try:
        import license as lic_mod
        lic_module = lic_mod
        machine_id = lic_mod.get_machine_id()
    except Exception as exc:
        add_log("error", f"Módulo de licença não carregado: {exc}")

    # ── 1. Load config.json ───────────────────────────────────────────────────
    local_cfg: dict = {}
    if CONFIG_PATH.exists():
        try:
            local_cfg = json.loads(CONFIG_PATH.read_text())
        except Exception:
            local_cfg = {}

    license_key = local_cfg.get("license_key", "")
    license_info = local_cfg.get("license_info_cache", {})

    # Ensure machine_id is not empty
    if not machine_id and lic_module:
        try:
            machine_id = lic_module.get_machine_id()
        except Exception:
            pass

    # ── 2. License validation ─────────────────────────────────────────────────
    if API_BASE and lic_module and license_key:
        try:
            license_info = lic_module.validate_license(license_key, machine_id)
            if not license_info.get("valid"):
                license_info = {}
        except lic_module.LicenseError as exc:
            add_log("error", f"Licença inválida: {exc}")
            license_info = {}
        except Exception:
            # Network unreachable — use cached info only if it was previously valid
            cached = local_cfg.get("license_info_cache", {})
            if cached.get("valid"):
                license_info = cached
                add_log("warning", "API inacessível — usando cache. Período de graça: 30 min.")
            else:
                license_info = {}
                add_log("error", "API inacessível e sem cache válido. Licença não validada.")
    elif API_BASE and lic_module and not license_key:
        # API configured but no license key — user needs to activate
        license_info = {}
        add_log("info", "Nenhuma chave de licença configurada. Acesse a interface para ativar.")
    else:
        # No API configured — cannot run in production mode
        add_log("error", "API de licença não configurada (APRO_API_BASE). O bot não pode iniciar.")
        license_info = {}

    # ── 3. Check for update ─────────────────────────────────────────────────
    if API_BASE:
        try:
            import updater
            updater.check_and_update(VERSION, API_BASE)
        except Exception:
            pass

    # ── 4. Load config ────────────────────────────────────────────────────────
    if API_BASE and license_key:
        try:
            import config_loader as cl
            config_loader = cl
            remote_cfg = cl.fetch_config(license_key, machine_id)
        except Exception as exc:
            config_error = str(exc)
            add_log("error", config_error)
            remote_cfg = _load_env_fallback()
    else:
        remote_cfg = _load_env_fallback()
        if not config_error:
            add_log("info", "Config carregada do arquivo .env local.")

    # ── 5. Start BotRunner ────────────────────────────────────────────────────
    from bot_runner import BotRunner
    runner = BotRunner(log_callback=add_log)

    can_start = True
    if not remote_cfg.get("api_id") or not remote_cfg.get("api_hash"):
        add_log("warning", "API_ID ou API_HASH ausentes. O bot não iniciará automaticamente.")
        can_start = False
    
    if not remote_cfg.get("sources"):
        add_log("info", "Nenhum grupo de origem configurado.")
        can_start = False

    if can_start:
        try:
            runner.start(remote_cfg)
        except Exception as exc:
            add_log("error", f"Erro ao iniciar bot: {exc}")
    else:
        add_log("info", "Aguardando configuração completa para iniciar.")

    # ── 6. Start heartbeat ────────────────────────────────────────────────────
    if API_BASE and lic_module and license_key:
        try:
            # Callback when grace period expires — stop the bot
            def _on_grace_expired():
                add_log("error", "Período de graça da licença expirado. Parando bot...")
                if runner:
                    runner.stop()
            
            lic_module.start_heartbeat(license_key, machine_id, on_grace_expired=_on_grace_expired)
        except Exception:
            pass
            
    # ── 6.5 Start WhatsApp Bridge Subprocess ──────────────────────────────────
    import atexit
    wpp_process = None
    bridge_path = None
    if getattr(sys, "frozen", False):
        bridge_path = Path(sys._MEIPASS) / "whatsapp_bridge.exe"
    else:
        bridge_path = Path(__file__).parent / "whatsapp_bridge.exe"
        if not bridge_path.exists():
            bridge_path = Path(__file__).parent / "dist" / "whatsapp_bridge.exe"
        
    if bridge_path and bridge_path.exists():
        add_log("info", "Iniciando WhatsApp Bridge Integrado...")
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            wpp_process = subprocess.Popen(
                [str(bridge_path)],
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            atexit.register(lambda: wpp_process.kill() if wpp_process else None)
        except Exception as exc:
            add_log("error", f"Falha ao iniciar bridge WhatsApp: {exc}")
    else:
        add_log("warning", "whatsapp_bridge.exe não encontrado! Certifique-se de compilá-lo.")


    # ── 7. Serve Flask ────────────────────────────────────────────────────────
    _start_flask(
        runner=runner,
        machine_id=machine_id,
        license_key=license_key,
        license_info=license_info,
        remote_cfg=remote_cfg,
        error_msg=config_error,
        config_loader=config_loader,
        lic_module=lic_module,
    )


def _start_flask(
    runner,
    machine_id: str,
    license_key: str,
    license_info: dict,
    remote_cfg: dict,
    error_msg: str,
    config_loader,
    lic_module,
) -> None:
    # Locate templates inside the PyInstaller bundle or dev folder
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent

    template_dir = base / "web" / "templates"
    static_dir = base / "web" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.secret_key = os.urandom(24)

    def _is_activated() -> bool:
        return bool(license_info.get("valid"))

    # ── HTML pages ─────────────────────────────────────────────────────────────

    @app.get("/")
    def dashboard():
        if not _is_activated():
            return redirect(url_for("activate"))
        return render_template("dashboard.html", version=VERSION)

    @app.get("/activate")
    def activate():
        if _is_activated():
            return redirect(url_for("dashboard"))
        return render_template("activate.html", error=error_msg)

    @app.get("/config")
    def config_page():
        if not _is_activated():
            return redirect(url_for("activate"))
        return render_template("config.html")

    @app.get("/whatsapp")
    def whatsapp_page():
        if not _is_activated():
            return redirect(url_for("activate"))
        return render_template("whatsapp.html")

    @app.get("/logs")
    def logs_page():
        if not _is_activated():
            return redirect(url_for("activate"))
        return render_template("logs.html")

    # ── API endpoints ──────────────────────────────────────────────────────────

    @app.post("/api/activate")
    def api_activate():
        nonlocal license_key, license_info
        key = (request.json or {}).get("license_key", "").strip().upper()
        if not key:
            return jsonify({"ok": False, "error": "Chave inválida."}), 400

        if not API_BASE or not lic_module:
            return jsonify({"ok": False, "error": "API de licença não configurada."}), 503

        try:
            info = lic_module.validate_license(key, machine_id)
        except lic_module.LicenseError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 403
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Servidor inacessível: {exc}"}), 503

        if not info.get("valid"):
            return jsonify({"ok": False, "error": "Chave não autorizada para esta máquina."}), 403

        CONFIG_PATH.write_text(json.dumps({
            "license_key": key,
            "machine_id": machine_id,
            "license_info_cache": info,
        }))
        license_key = key
        license_info = info

        try:
            def _on_grace_expired():
                add_log("error", "Período de graça da licença expirado. Parando bot...")
                if runner:
                    runner.stop()
            lic_module.start_heartbeat(key, machine_id, on_grace_expired=_on_grace_expired)
        except Exception:
            pass

        return jsonify({"ok": True})

    @app.get("/api/status")
    def api_status():
        r_status = runner.status() if runner else "stopped"
        stats = runner.get_stats() if runner else {}
        return jsonify({
            "running": r_status == "running",
            "status": r_status,
            "stats": stats,
            "license_expires": license_info.get("expires_at"),
            "version": VERSION,
            "plan": license_info.get("plan", "local"),
        })

    @app.post("/api/bot/start")
    def api_bot_start():
        if runner is None:
            return jsonify({"ok": False, "error": "Runner não inicializado."}), 500
        try:
            if config_loader and license_key:
                cfg = config_loader.fetch_config(license_key, machine_id)
            else:
                cfg = _load_env_fallback()
            
            if not cfg.get("api_id") or not cfg.get("api_hash"):
                return jsonify({"ok": False, "error": "API_ID ou API_HASH ausentes. Configure nas definições."}), 400
                
            runner.start(cfg)
            add_log("success", "Bot iniciado pelo usuário.")
            return jsonify({"ok": True})
        except Exception as exc:
            add_log("error", f"Erro ao iniciar: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.post("/api/bot/stop")
    def api_bot_stop():
        if runner:
            runner.stop()
            add_log("info", "Bot parado pelo usuário.")
        return jsonify({"ok": True})

    @app.post("/api/ml/login")
    def api_ml_login():
        try:
            from affiliates import mercadolivre
            mercadolivre.open_login_page_sync()
            return jsonify({"ok": True})
        except Exception as e:
            add_log("error", f"Falha ao abrir ML login: {e}")
            return jsonify({"ok": False, "error": str(e)})

    @app.post("/api/bot/submit_code")
    def api_bot_submit_code():
        if runner is None:
            return jsonify({"ok": False, "error": "Runner não inicializado."}), 500
        
        data = request.json or {}
        code = data.get("code", "").strip()
        password = data.get("password", "").strip()
        
        res = runner.submit_code(code, password)
        if res.get("ok"):
            session_str = res.get("session_string", "")
            try:
                if config_loader and license_key:
                    config_loader.push_config(license_key, machine_id, {"session_string": session_str})
                
                env_path = Path(".env.local")
                if env_path.exists():
                    lines = env_path.read_text().splitlines()
                else:
                    lines = []
                lines = [l for l in lines if not l.startswith("TELEGRAM_SESSION_STRING=")]
                lines.append(f"TELEGRAM_SESSION_STRING={session_str}")
                env_path.write_text("\n".join(lines))
            except Exception as exc:
                add_log("error", f"Aviso: sessão não salva na config: {exc}")
                
            add_log("success", "Autenticação concluída! O bot está conectado.")
        return jsonify(res)

    @app.get("/api/config")
    def api_config_get():
        try:
            if config_loader and license_key:
                cfg = config_loader.fetch_config(license_key, machine_id)
            else:
                cfg = _load_env_fallback()
            masked = dict(cfg)
            for field in ("shopee_token", "ali_key", "ali_secret", "ali_tracking", "ml_token", "api_hash", "api_id"):
                if masked.get(field):
                    masked[field] = "••••••••"
            return jsonify(masked)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.post("/api/config")
    def api_config_save():
        data: dict = request.json or {}
        clean = {k: v for k, v in data.items() if v != "••••••••"}
        try:
            env_path = Path(".env.local")
            env_dict = {}
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        env_dict[k.strip()] = v.strip()

            if config_loader and license_key:
                try:
                    full_cfg = config_loader.fetch_config(license_key, machine_id)
                except Exception:
                    full_cfg = _load_env_fallback()
            else:
                full_cfg = _load_env_fallback()
            
            old_critical = {k: full_cfg.get(k) for k in ("api_id", "api_hash", "phone", "sources")}
            full_cfg.update(clean)
            new_critical = {k: full_cfg.get(k) for k in ("api_id", "api_hash", "phone", "sources")}
            
            if config_loader and license_key:
                config_loader.push_config(license_key, machine_id, full_cfg)
            
            mapping = {
                "api_id": "API_ID",
                "api_hash": "API_HASH",
                "phone": "TELEGRAM_PHONE",
                "destination_telegram": "DESTINATION",
                "delay_segundos": "DELAY",
                "whatsapp_endpoint": "WHATSAPP_ENDPOINT",
                "shopee_token": "SHOPEE_TOKEN",
                "ali_key": "ALIEXPRESS_APP_KEY",
                "ali_secret": "ALIEXPRESS_APP_SECRET",
                "ali_tracking": "ALIEXPRESS_TRACKING_ID",
                "ml_token": "ML_TOKEN",
                "send_telegram": "ENABLE_TELEGRAM",
                "send_whatsapp": "ENABLE_WHATSAPP",
                "conv_shopee": "CONV_SHOPEE",
                "conv_ali": "CONV_ALI",
                "conv_ml": "CONV_ML",
            }
            for cfg_k, env_k in mapping.items():
                if cfg_k in full_cfg and full_cfg[cfg_k] is not None:
                    env_dict[env_k] = str(full_cfg[cfg_k])
            
            if "sources" in full_cfg:
                env_dict["SOURCE"] = ",".join(full_cfg["sources"])
            if "wpp_destinations" in full_cfg:
                env_dict["WHATSAPP_DESTINATIONS"] = ",".join(full_cfg["wpp_destinations"])

            new_lines = [f"{k}={v}" for k, v in env_dict.items()]
            env_path.write_text("\n".join(new_lines))
            
            if runner:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=".env.local", override=True)
                
                try:
                    if config_loader and license_key:
                        fresh_cfg = config_loader.fetch_config(license_key, machine_id)
                    else:
                        fresh_cfg = _load_env_fallback()
                    
                    if old_critical != new_critical and runner.status() == "running":
                        add_log("info", "Mudanças críticas detectadas. Reiniciando bot...")
                        runner.stop()
                        time.sleep(1)
                        runner.start(fresh_cfg)
                    else:
                        runner.update_config(fresh_cfg)
                except Exception as exc:
                    add_log("error", f"Falha ao atualizar bot: {exc}")
            
            add_log("success", "Configurações salvas e aplicadas.")
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/logs")
    def api_logs():
        with _lock:
            return jsonify(list(_logs))

    @app.post("/api/logs/clear")
    def api_logs_clear():
        with _lock:
            _logs.clear()
        return jsonify({"ok": True})
        
    @app.get("/api/whatsapp/status")
    def api_whatsapp_status():
        if not _is_activated(): return jsonify({"error": "unauthorized"}), 401
        try:
            r = requests.get("http://localhost:4000/status", timeout=2)
            return jsonify(r.json())
        except Exception:
            return jsonify({"status": "disconnected", "qr": ""})

    # ── Open browser then serve ────────────────────────────────────────────────
    route = "/" if _is_activated() else "/activate"
    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}{route}")).start()

    add_log("info", f"Interface disponível em http://127.0.0.1:{LOCAL_PORT}")

    app.run(host="127.0.0.1", port=LOCAL_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    _boot()
