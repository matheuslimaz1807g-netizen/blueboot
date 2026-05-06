"""
main.py — Entry Point Unificado do BlueBot.

Detecta automaticamente se está rodando em modo Pessoal (VPS/.env) 
ou Modo Gerenciado (Licença/API).
"""
from __future__ import annotations

import asyncio
import json
import os
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

# ── Configurações Globais ──────────────────────────────────────────────────────
VERSION = "2.0.0"
MAX_LOGS = 300
LOCAL_PORT = 8080

_logs: deque[dict] = deque(maxlen=MAX_LOGS)
_lock = threading.Lock()
_runner: BotRunner = None


def add_log(nivel: str, mensagem: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = {"nivel": nivel, "mensagem": mensagem, "horario": ts}
    with _lock:
        _logs.append(entry)
    # Print unbuffered para o Docker logs
    print(f"[{ts}] [{nivel.upper()}] {mensagem}", flush=True)


# ── Templates HTML (Embutidos para Portabilidade na VPS) ──────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>BlueBot v{{ version }} — Painel</title>
    <meta http-equiv="refresh" content="10">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 20px; }
        .status-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; display: flex; gap: 20px; }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        .badge-running { background: #238636; color: white; }
        .badge-stopped { background: #da3633; color: white; }
        .log-container { background: #010409; border: 1px solid #30363d; border-radius: 8px; padding: 15px; height: 500px; overflow-y: auto; font-family: monospace; font-size: 13px; margin-top: 20px; }
        .log-entry { margin-bottom: 4px; border-bottom: 1px solid #161b22; padding-bottom: 2px; }
        .ts { color: #8b949e; }
        .nivel-info { color: #58a6ff; }
        .nivel-success { color: #3fb950; }
        .nivel-warning { color: #d29922; }
        .nivel-error { color: #f85149; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>BlueBot <small style="font-size: 12px; color: #8b949e;">v{{ version }}</small></h1>
            <div>
                {% if status == 'running' %}
                <span class="badge badge-running">Rodando</span>
                {% else %}
                <span class="badge badge-stopped">Parado</span>
                {% endif %}
            </div>
        </div>

        <div class="status-card">
            <div>
                <strong>Modo:</strong> {{ mode }}<br>
                <strong>Plataformas:</strong> Telegram {% if wpp %} + WhatsApp{% endif %}
            </div>
            <div style="margin-left: auto; text-align: right;">
                <strong>Mensagens Processadas:</strong> {{ stats.get('processed', 0) }}<br>
                <strong>Links Convertidos:</strong> {{ stats.get('converted', 0) }}
            </div>
        </div>

        <div class="log-container">
            {% for log in logs|reverse %}
            <div class="log-entry">
                <span class="ts">[{{ log.horario }}]</span> 
                <span class="nivel-{{ log.nivel }}">[{{ log.nivel|upper }}]</span> 
                {{ log.mensagem }}
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""


def create_app(mode: str, initial_config: dict):
    app = Flask(__name__)
    
    # Credenciais do Painel
    DASH_USER = os.getenv("DASHBOARD_USER", "admin")
    DASH_PWD = os.getenv("DASHBOARD_PASSWORD", "admin123")

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
    @requires_auth
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
        return jsonify(result)

    @app.route("/api/whatsapp/status")
    @requires_auth
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
                resp = requests.post(
                    f"{api_base}/license/discover",
                    headers={"X-Install-Token": install_token or ""},
                    json={
                        "machine_id": mid,
                        "hostname": platform.node(),
                        "platform": f"{platform.system()} {platform.release()}",
                        "label": robot_label or "BlueBot"
                    },
                    timeout=10,
                    verify=False
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
                wpp_url = config.get("whatsapp_endpoint", "http://whatsapp:4000/send").replace("/send", "/status")
                r = requests.get(wpp_url, timeout=5)
                if r.status_code == 200:
                    d = r.json()
                    return {
                        "whatsapp_status": d.get("status"),
                        "whatsapp_qr": d.get("qr")
                    }
            except:
                pass
            return {}

        start_heartbeat(license_key, mid, on_grace_expired=on_expired, status_callback=get_wpp_status_callback)
        
        # 3. Carregar Configuração (Remota primeiro, fallback para local)
        # Carrega a local como base
        config = config_loader.load_config_from_env()
        
        try:
            add_log("info", "📡 Buscando configurações remotas do painel...")
            remote_config = config_loader.fetch_remote_config(license_key, mid)
            # Mescla remota sobre a local
            config = config_loader.merge_configs(config, remote_config)
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

    # Iniciar Polling de Autenticação para buscar códigos remotos via Painel
    def poll_auth_code():
        while True:
            try:
                if _runner.status() == "waiting_code":
                    resp = requests.get(
                        f"{api_base}/license/auth-code",
                        params={"license_key": license_key, "machine_id": mid},
                        verify=False,
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
                                    # Update remote config with new session_string
                                    cfg_resp = requests.get(
                                        f"{api_base}/config/{license_key}",
                                        params={"machine_id": mid},
                                        verify=False,
                                        timeout=5
                                    )
                                    if cfg_resp.status_code == 200:
                                        cfg = cfg_resp.json()
                                        cfg["session_string"] = session_str
                                        requests.put(
                                            f"{api_base}/config/{license_key}",
                                            params={"machine_id": mid},
                                            json=cfg,
                                            verify=False,
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
