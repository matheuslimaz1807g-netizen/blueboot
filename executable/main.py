"""
main.py — Entry Point Unificado do BlueBot.

Detecta automaticamente se está rodando em modo Pessoal (VPS/.env) 
ou Modo Gerenciado (Licença/API).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import threading
import time
import webbrowser
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, render_template_string, request, url_for

import config_loader
from bot_runner import BotRunner
from functools import wraps
from utils import should_verify_ssl

# ── Configurações Globais ──────────────────────────────────────────────────────
VERSION = "2.0.0"
MAX_LOGS = 300
LOCAL_PORT = 8080

_logs: deque[dict] = deque(maxlen=MAX_LOGS)
_lock = threading.Lock()
_runner: BotRunner = None
_last_sent_log_index: int = 0  # Tracks last log index sent to server (deduplication)
ENV_SYNC_FIELDS = {
    "ml_cookies": "ML_COOKIES",
    "ml_token": "ML_TOKEN",
    "shopee_token": "SHOPEE_TOKEN",
    "ali_key": "ALIEXPRESS_APP_KEY",
    "ali_secret": "ALIEXPRESS_APP_SECRET",
    "ali_tracking": "ALIEXPRESS_TRACKING_ID",
}


def add_log(nivel: str, mensagem: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = {"nivel": nivel, "mensagem": mensagem, "horario": ts}
    with _lock:
        _logs.append(entry)
    # Print unbuffered para o Docker logs
    print(f"[{ts}] [{nivel.upper()}] {mensagem}", flush=True)


def find_env_file() -> Path | None:
    for f in [".env.local", ".env"]:
        path = Path(f)
        if path.exists():
            return path
    return None


def save_values_to_env(values: dict[str, str]) -> bool:
    env_path = find_env_file()
    if not env_path:
        if os.getenv("DOCKER_CONTAINER"):
            add_log("warning", "Arquivo .env nao encontrado no container. Monte ./.env:/app/.env para persistir configs remotas.")
            return False
        env_path = Path(".env")

    try:
        content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        lines = content.splitlines()
        pending = dict(values)
        new_lines = []

        for line in lines:
            stripped = line.strip()
            key = stripped.split("=", 1)[0] if "=" in stripped and not stripped.startswith("#") else None
            if key in pending:
                new_lines.append(f"{key}={pending.pop(key)}")
            else:
                new_lines.append(line)

        if pending and new_lines and new_lines[-1] != "":
            new_lines.append("")
        for key, value in pending.items():
            new_lines.append(f"{key}={value}")

        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        add_log("warning", f"Nao foi possivel atualizar o .env: {exc}")
        return False


def sync_env_vars(config: dict, persist: bool = False) -> None:
    updates: dict[str, str] = {}
    for cfg_key, env_key in ENV_SYNC_FIELDS.items():
        if cfg_key not in config:
            continue
        value = config.get(cfg_key)
        if value is None:
            continue
        if value == "":
            os.environ.pop(env_key, None)
            updates[env_key] = ""
            continue
        os.environ[env_key] = str(value)
        updates[env_key] = str(value)

    if persist and updates:
        save_values_to_env(updates)

    if "ML_COOKIES" in updates:
        add_log("info", f"ML_COOKIES sincronizado: {len(updates['ML_COOKIES'])} caracteres.")


def save_session_to_env(session_string: str) -> bool:
    """
    Salva a TELEGRAM_SESSION_STRING no arquivo .env local.
    Isso garante que a sessão persista mesmo após restart do container.
    
    Procura pelos arquivos .env ou .env.local no diretório atual.
    Se a variável já existir, substitui; senão, adiciona ao final.
    """
    env_path = find_env_file()
    
    if not env_path:
        # Se nenhum .env existir, cria um .env
        env_path = Path(".env")
        add_log("warning", f"⚠️ Arquivo .env não encontrado. Criando {env_path}...")
    
    try:
        content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        lines = content.splitlines()
        
        # Procura por TELEGRAM_SESSION_STRING nas linhas existentes
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("TELEGRAM_SESSION_STRING"):
                new_lines.append(f"TELEGRAM_SESSION_STRING={session_string}")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            # Adiciona ao final do arquivo
            if new_lines and new_lines[-1] != "":
                new_lines.append("")
            new_lines.append(f"TELEGRAM_SESSION_STRING={session_string}")
        
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        add_log("success", f"✅ Session string salva em {env_path.name} com sucesso!")
        return True
        
    except Exception as e:
        add_log("error", f"❌ Erro ao salvar session string no .env: {e}")
        return False


# ── Templates HTML ─────────────────────────────────────────────────────────────
# Template carregado de arquivo externo para facilitar manutenção.
# Localização: executable/templates/dashboard.html
DASHBOARD_HTML = (Path(__file__).parent / "templates" / "dashboard.html").read_text(encoding="utf-8")


def create_app(mode: str, initial_config: dict):
    app = Flask(__name__)
    
    # Credenciais do Painel
    DASH_USER = os.getenv("DASHBOARD_USER", "admin")
    DASH_PWD = (
        os.getenv("DASHBOARD_PASSWORD")
        or os.getenv("CLIENT_PASSWORD")
        or os.getenv("INSTALL_TOKEN")
    )
    if not DASH_PWD:
        # Ultimo recurso: derivar da FERNET_KEY para nunca crashar
        fk = os.getenv("FERNET_KEY", "")
        DASH_PWD = fk[:16] if fk else "bluebot"
        print(f"[WARNING] DASHBOARD_PASSWORD nao definida. Usando fallback automatico.")

    def check_auth(username, password):
        return username == DASH_USER and password == DASH_PWD

    def authenticate():
        return ("Acesso negado. Por favor, faça login.", 401, {
            'WWW-Authenticate': 'Basic realm="Login Requerido"'
        })

    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
            return f(*args, **kwargs)
        return decorated

    @app.route("/")
    @requires_auth
    def index():
        return render_template_string(
            DASHBOARD_HTML,
            version=VERSION,
            mode=mode,
            status=_runner.status() if _runner else "stopped",
            stats=_runner.get_stats() if _runner else {},
            logs=list(_logs),
            wpp=initial_config.get("send_whatsapp", False)
        )

    @app.route("/api/status")
    def status():
        return jsonify({
            "status": _runner.status() if _runner else "stopped",
            "version": VERSION,
            "mode": mode,
            "stats": _runner.get_stats() if _runner else {}
        })

    @app.route("/api/auth-code", methods=["POST"])
    @requires_auth
    def submit_auth_code():
        """Endpoint para receber o código de verificação do Telegram."""
        if not _runner:
            return jsonify({"ok": False, "error": "Bot não iniciado"}), 400
        
        data = request.get_json(silent=True) or {}
        code = data.get("code", "").strip()
        password = data.get("password", "").strip()
        
        if not code and not password:
            return jsonify({"ok": False, "error": "Código ou senha é obrigatório"}), 400
        
        result = _runner.submit_code(code, password)
        
        # Salva a session string localmente se a autenticação foi bem-sucedida
        if result.get("ok") and result.get("session_string"):
            save_session_to_env(result["session_string"])
        
        return jsonify(result)

    @app.route("/api/whatsapp/status")
    def whatsapp_status():
        """Endpoint para consultar o status do WhatsApp via container dedicado."""
        try:
            import requests
            wpp_url = os.getenv("WHATSAPP_ENDPOINT", "http://whatsapp:4000/send").replace("/send", "/status")
            resp = requests.get(wpp_url, timeout=5)
            return jsonify(resp.json())
        except Exception as e:
            return jsonify({"status": "error", "message": f"Erro ao conectar ao serviço WhatsApp: {str(e)}"}), 500

    return app


def main():
    global _runner
    add_log("info", f"Iniciando BlueBot v{VERSION}...")
    add_log("info", "🔒 MODO: Gerenciado (Licenciado)")

    # 1. Carregar Configuração Local (Variáveis de Ambiente do .env)
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Padronizado: .env.local -> .env
    for f in [".env.local", ".env"]:
        if Path(f).exists():
            load_dotenv(dotenv_path=f, override=False)
    
    api_base = os.getenv("APRO_API_BASE") or os.getenv("API_BASE_URL", "http://license_api:8000")
    license_key = os.getenv("LICENSE_KEY", "").strip()
    robot_label = os.getenv("ROBOT_LABEL", "") 
    install_token = os.getenv("INSTALL_TOKEN", "") # Senha global de segurança
    
    from license import get_machine_id, validate_license, start_heartbeat
    import platform
    import requests

    mid = get_machine_id()
    
    # ⚠️ MODO GERENCIADO OBRIGATÓRIO: Sempre exigir LICENSE_KEY
    if not license_key:
        add_log("warning", "⏳ Nenhuma LICENSE_KEY detectada.")
        add_log("info", "")
        add_log("info", "📋 INFORMAÇÕES DESTA MÁQUINA:")
        add_log("info", f"   Machine ID:  {mid}")
        add_log("info", f"   Hostname:    {platform.node()}")
        add_log("info", f"   Platform:    {platform.system()} {platform.release()}")
        add_log("info", "")
        add_log("info", "⚙️ Conectando ao Painel Admin para auto-descoberta...")
        add_log("info", f"   Painel: {api_base}")
        add_log("info", "")
        add_log("success", "✅ Robô aguardando aprovação no Painel Admin...")
        add_log("info", "   📱 Vá ao Painel, localize esta máquina e clique em AUTORIZAR")
        add_log("info", "   ⏱️ Tentando a cada 10 segundos... (Ctrl+C para cancelar)")
        add_log("info", "")
        
        # Loop de auto-descoberta com tentativas frequentes
        attempt = 0
        failed_attempts = 0
        
        while not license_key:
            attempt += 1
            
            try:
                # Tenta descobrir automaticamente no painel
                discover_url = f"{api_base}/license/discover"
                resp = requests.post(
                    discover_url,
                    headers={"X-Install-Token": install_token or ""},
                    json={
                        "machine_id": mid,
                        "hostname": platform.node(),
                        "platform": f"{platform.system()} {platform.release()}",
                        "label": robot_label or "BlueBot"
                    },
                    timeout=10,
                    verify=should_verify_ssl(discover_url)
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("assigned_key"):
                        license_key = data.get("assigned_key")
                        add_log("success", f"🎉 LICENÇA AUTORIZADA PELO PAINEL!")
                        add_log("success", f"   Chave: {license_key[:16]}***")
                        add_log("info", "   Iniciando sistema...")
                        failed_attempts = 0
                        break
                    elif data.get("pending"):
                        if attempt % 6 == 0:  # Log a cada 60 segundos
                            add_log("info", f"⏳ Aguardando aprovação... (Tentativa {attempt})")
                    else:
                        if failed_attempts == 0:
                            add_log("warning", "📍 Robô registrado no painel. Aguardando aprovação admin...")
                        failed_attempts += 1
                        
                elif resp.status_code == 401:
                    add_log("error", "❌ INSTALL_TOKEN inválido!")
                    add_log("error", "   Verifique a variável INSTALL_TOKEN no .env")
                    time.sleep(30)
                    continue
                    
                elif resp.status_code == 403:
                    if attempt == 1:
                        add_log("warning", "⚠️ Acesso negado ao Painel Admin")
                    time.sleep(30)
                    continue
                
                else:
                    if attempt == 1 or attempt % 10 == 0:
                        add_log("warning", f"Painel retornou: {resp.status_code}")
                    
            except requests.exceptions.ConnectionError as e:
                if attempt == 1:
                    add_log("warning", f"⚠️ Não conseguiu conectar ao painel em {api_base}")
                    add_log("warning", f"   Erro: {str(e)[:100]}")
                elif attempt % 12 == 0:  # Log a cada 2 minutos
                    add_log("warning", f"Ainda tentando conectar ao painel... (Tentativa {attempt})")
                    
            except Exception as e:
                if attempt == 1 or attempt % 20 == 0:
                    add_log("warning", f"Erro na auto-descoberta: {str(e)[:100]}")
            
            # Aguarda antes da próxima tentativa (10 segundos)
            time.sleep(10)

    # ✅ Modo Gerenciado Confirmado
    mode = "Gerenciado"
    add_log("info", f"🔐 Validando licença {license_key[:8]}... (ID: {mid[:6]})")
    
    try:
        # 1. Validar Licença no Servidor
        os.environ["APRO_API_BASE"] = api_base # Garante que o license.py use a URL certa
        lic_info = validate_license(license_key, mid)
        add_log("success", f"✅ Licença VALIDADA! Plano: {lic_info.get('plan', 'basic').upper()}")
        
        # 2. Iniciar Heartbeat (Batimento para o painel)
        def on_expired():
            add_log("error", "❌ Sinal de licença perdido ou expirado. Encerrando robô...")
            os._exit(1)
        
        def get_wpp_status_callback():
            """Busca o status do WhatsApp local para enviar ao painel master."""
            try:
                import requests
                # Pega a URL do WhatsApp da config e muda /send para /status
                wpp_url = os.getenv("WHATSAPP_ENDPOINT", "http://whatsapp:4000/send").replace("/send", "/status")
                r = requests.get(wpp_url, timeout=5)
                if r.status_code == 200:
                    d = r.json()
                    status = d.get("status")
                    qr = d.get("qr")
                    if qr:
                        add_log("info", f"💓 QR Code detectado e pronto para envio (Tam: {len(qr)})")
                    return {
                        "whatsapp_status": status,
                        "whatsapp_qr": qr
                    }
                else:
                    add_log("warning", f"💓 Falha ao buscar status WPP: Status {r.status_code}")
            except Exception as e:
                add_log("warning", f"💓 Erro na conexão com WhatsApp: {e}")
            return {}

        def get_pending_logs_callback():
            """Retorna logs pendentes desde o último envio (para o heartbeat)."""
            global _last_sent_log_index
            with _lock:
                all_logs = list(_logs)
            
            current_len = len(all_logs)
            if current_len <= _last_sent_log_index:
                # Deque foi resetada ou nada novo
                if current_len < _last_sent_log_index:
                    _last_sent_log_index = 0
                return []
            
            # Pega apenas os novos
            new_logs = all_logs[_last_sent_log_index:]
            _last_sent_log_index = current_len
            
            # Converte para formato do schema HeartbeatLogItem
            return [
                {"nivel": log.get("nivel", "info"), "mensagem": log.get("mensagem", ""), "horario": log.get("horario", "")}
                for log in new_logs[:50]  # Max 50 per cycle
            ]

        start_heartbeat(license_key, mid, on_grace_expired=on_expired, status_callback=get_wpp_status_callback, logs_callback=get_pending_logs_callback)
        
        # 3. Carregar Configuração (Remota primeiro, fallback para local)
        # Carrega a local como base
        config = config_loader.load_config_from_env()
        
        try:
            add_log("info", "📡 Buscando configurações remotas do painel...")
            remote_config = config_loader.fetch_remote_config(license_key, mid)
            # Mescla remota sobre a local
            config = config_loader.merge_configs(config, remote_config)
            sync_env_vars(config, persist=True)
            add_log("success", "✅ Configurações remotas aplicadas e mescladas com local!")
        except Exception as e:
            add_log("warning", f"⚠️ Config remota indisponível ou vazia ({e})")
            add_log("info", "📁 Mantendo configurações locais (.env).")
        
        add_log("info", "✨ Sistema de licenciamento e gestão remota ATIVO.")
        
    except Exception as e:
        add_log("error", f"❌ FALHA CRÍTICA DE LICENÇA: {e}")
        add_log("error", "O robô será encerrado. Verifique sua LICENSE_KEY e tente novamente.")
        time.sleep(5)
        sys.exit(1)

    # 2. Iniciar Bot
    _runner = BotRunner(log_callback=add_log)
    if config.get("api_id") and config.get("api_hash"):
        try:
            _runner.start(config)
        except Exception as e:
            add_log("error", f"❌ Falha ao iniciar BotRunner: {e}")
    else:
        add_log("warning", "⚠️ API_ID/HASH ausentes. Bot de Telegram não iniciado.")

    # Iniciar Config Watcher: verifica periodicamente se a config remota mudou
    # e reinicia o bot se necessário (qualquer campo alterado no painel)
    def config_watcher():
        # Campos monitorados (exclui session_string para evitar loop de reinicialização)
        MONITORED_FIELDS = {
            "phone", "api_id", "api_hash", "sources",
            "destination_telegram", "delay_segundos", "send_telegram", 
            "send_whatsapp", "wpp_destinations", "whatsapp_endpoint",
            "conv_shopee", "conv_ali", "conv_ml",
            "shopee_token", "ali_key", "ali_secret", "ali_tracking",
            "ml_token", "ml_cookies", "web_api_url", "send_to_web_api"
        }
        # Campos que exigem reinicialização do bot
        RESTART_FIELDS = {"phone", "api_id", "api_hash", "sources"}
        
        # Snapshot inicial
        def make_snapshot(cfg):
            return {k: cfg.get(k) for k in MONITORED_FIELDS}
        
        last_snapshot = make_snapshot(config)
        
        while True:
            try:
                time.sleep(30)
                if not license_key:
                    continue
                    
                remote = config_loader.fetch_remote_config(license_key, mid)
                if not remote:
                    continue
                
                merged = config_loader.merge_configs(dict(config), remote)
                new_snapshot = make_snapshot(merged)
                
                changed_fields = []
                needs_restart = False
                
                for field in MONITORED_FIELDS:
                    old_val = last_snapshot.get(field)
                    new_val = new_snapshot.get(field)
                    
                    if isinstance(old_val, list):
                        old_val = sorted(old_val) if old_val else []
                    if isinstance(new_val, list):
                        new_val = sorted(new_val) if new_val else []
                    
                    if old_val != new_val:
                        changed_fields.append(field)
                        if field in RESTART_FIELDS:
                            needs_restart = True
                
                if changed_fields:
                    add_log("info", f"🔄 Painel alterou: {', '.join(changed_fields)}")
                    
                    if needs_restart:
                        add_log("info", "🔄 Reiniciando bot...")
                        _runner.stop()
                        time.sleep(2)
                    
                    config.update(merged)
                    last_snapshot = new_snapshot
                    
                    sync_env_vars(merged, persist=True)
                    
                    if needs_restart:
                        try:
                            _runner.start(merged)
                            add_log("success", "✅ Bot reiniciado!")
                        except Exception as e:
                            add_log("error", f"❌ Falha ao reiniciar: {e}")
                    else:
                        _runner.update_config(merged)
                        add_log("success", "✅ Config atualizada!")
                        
            except Exception:
                pass

    threading.Thread(target=config_watcher, daemon=True, name="ConfigWatcher").start()

    # Iniciar Polling de Autenticação para buscar códigos remotos via Painel
    def poll_auth_code():
        while True:
            try:
                if _runner.status() == "waiting_code":
                    auth_code_url = f"{api_base}/license/auth-code"
                    resp = requests.get(
                        auth_code_url,
                        params={"license_key": license_key, "machine_id": mid},
                        verify=should_verify_ssl(auth_code_url),
                        timeout=5
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("has_code"):
                            code = data.get("code")
                            pwd = data.get("password", "")
                            add_log("info", "🔑 Código recebido do painel. Autenticando...")
                            res = _runner.submit_code(code, pwd)
                            if res.get("ok"):
                                add_log("success", "✅ Autenticação Telegram concluída via painel!")
                                session_str = res.get("session_string")
                                if session_str:
                                    # 1. Salva LOCALMENTE no .env para persistir após restart
                                    save_session_to_env(session_str)
                                    
                                    # 2. Update remote config with new session_string
                                    cfg_url = f"{api_base}/config/{license_key}"
                                    cfg_resp = requests.get(
                                        cfg_url,
                                        params={"machine_id": mid},
                                        verify=should_verify_ssl(cfg_url),
                                        timeout=5
                                    )
                                    if cfg_resp.status_code == 200:
                                        cfg = cfg_resp.json()
                                        cfg["session_string"] = session_str
                                        requests.put(
                                            cfg_url,
                                            params={"machine_id": mid},
                                            json=cfg,
                                            verify=should_verify_ssl(cfg_url),
                                            timeout=5
                                        )
                            elif res.get("requires_password"):
                                add_log("warning", "⚠️ Senha de duas etapas necessária! Insira no painel.")
                            else:
                                add_log("error", f"❌ Erro na autenticação: {res.get('error')}")
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=poll_auth_code, daemon=True, name="AuthCodePoller").start()

    # 3. Iniciar Flask Dashboard
    app = create_app(mode, config)
    
    # Rodar Flask em thread separada ou no main loop
    # Na VPS (Docker), rodamos no main thread para manter o container vivo
    host = "0.0.0.0" if os.getenv("DOCKER_CONTAINER") or not sys.stdin.isatty() else "127.0.0.1"
    
    if host == "127.0.0.1":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}")).start()

    add_log("success", f"🎯 Painel de controle rodando em http://{host}:{LOCAL_PORT}")
    add_log("info", f"🔒 Modo: {mode} | Licença: {license_key[:12]}***")
    app.run(host=host, port=LOCAL_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
