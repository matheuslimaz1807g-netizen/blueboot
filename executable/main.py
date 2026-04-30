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

    @app.route("/")
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

    return app


def main():
    global _runner
    add_log("info", f"Iniciando BlueBot v{VERSION}...")

    # 1. Carregar Configuração
    api_base = os.getenv("APRO_API_BASE", "")
    mode = "Gerenciado" if api_base else "Pessoal (VPS)"
    
    try:
        if api_base:
            # Modo Gerenciado (Precisa de licença)
            from license import get_machine_id, validate_license
            mid = get_machine_id()
            # Simplificação: tenta carregar licença do config.json se existir
            lic_path = Path("config.json")
            if lic_path.exists():
                lic_data = json.loads(lic_path.read_text())
                key = lic_data.get("license_key")
                config = config_loader.fetch_remote_config(key, mid)
            else:
                add_log("warning", "Modo gerenciado sem config.json. Usando .env fallback.")
                config = config_loader.load_config_from_env()
        else:
            # Modo Pessoal (Lê do .env)
            config = config_loader.load_config_from_env()
            add_log("info", "Configurações carregadas do .env (Modo Pessoal).")
    except Exception as e:
        add_log("error", f"Falha ao carregar configurações: {e}")
        config = config_loader.load_config_from_env()

    # 2. Iniciar Bot
    _runner = BotRunner(log_callback=add_log)
    if config.get("api_id") and config.get("api_hash"):
        try:
            _runner.start(config)
        except Exception as e:
            add_log("error", f"Falha ao iniciar BotRunner: {e}")
    else:
        add_log("warning", "API_ID/HASH ausentes. Bot não iniciado.")

    # 3. Iniciar Flask Dashboard
    app = create_app(mode, config)
    
    # Rodar Flask em thread separada ou no main loop
    # Na VPS (Docker), rodamos no main thread para manter o container vivo
    host = "0.0.0.0" if os.getenv("DOCKER_CONTAINER") or not sys.stdin.isatty() else "127.0.0.1"
    
    if host == "127.0.0.1" and mode == "Gerenciado":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}")).start()

    add_log("info", f"Painel de controle rodando em http://{host}:{LOCAL_PORT}")
    app.run(host=host, port=LOCAL_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
