"""
bot_runner_vps.py — Entry point para rodar o bot na VPS com painel web de status.

Lê tudo direto do .env e inicia o BotRunner + painel Flask em :8080.
"""
from __future__ import annotations

import os
import signal
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string

# Carrega o .env
load_dotenv(dotenv_path=".env", override=True)

# ── Log store compartilhado ────────────────────────────────────────────────────
_logs: deque[dict] = deque(maxlen=300)
_lock = threading.Lock()


def log(nivel: str, mensagem: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = {"nivel": nivel, "mensagem": mensagem, "horario": ts}
    with _lock:
        _logs.append(entry)
    print(f"[{ts}] [{nivel.upper()}] {mensagem}", flush=True)


def _load_config() -> dict:
    return {
        "api_id": os.getenv("API_ID", ""),
        "api_hash": os.getenv("API_HASH", ""),
        "phone": os.getenv("TELEGRAM_PHONE", ""),
        "session_string": os.getenv("TELEGRAM_SESSION_STRING", ""),
        "sources": [s.strip() for s in os.getenv("SOURCE", "").split(",") if s.strip()],
        "destination_telegram": os.getenv("DESTINATION", ""),
        "delay_segundos": int(os.getenv("DELAY", "3")),
        "wpp_destinations": [s.strip() for s in os.getenv("WHATSAPP_DESTINATIONS", "").split(",") if s.strip()],
        "whatsapp_endpoint": os.getenv("WHATSAPP_ENDPOINT", "http://whatsapp:4000/send"),
        "send_telegram": os.getenv("ENABLE_TELEGRAM", "true").lower() == "true",
        "send_whatsapp": os.getenv("ENABLE_WHATSAPP", "false").lower() == "true",
        "conv_shopee": os.getenv("CONV_SHOPEE", "true").lower() == "true",
        "conv_ali": os.getenv("CONV_ALI", "true").lower() == "true",
        "conv_ml": os.getenv("CONV_ML", "true").lower() == "true",
        "filtros": {},
        "shopee_token": os.getenv("SHOPEE_TOKEN", ""),
        "ali_key": os.getenv("ALIEXPRESS_APP_KEY", ""),
        "ali_secret": os.getenv("ALIEXPRESS_APP_SECRET", ""),
        "ali_tracking": os.getenv("ALIEXPRESS_TRACKING_ID", ""),
        "ml_token": os.getenv("ML_TOKEN", ""),
    }


# ── Painel HTML ────────────────────────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="10">
<title>BlueBot — Painel VPS</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Inter', sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; }
  .header { background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%); border-bottom: 1px solid #21262d; padding: 20px 32px; display: flex; align-items: center; gap: 12px; }
  .logo { width: 36px; height: 36px; background: linear-gradient(135deg, #2563eb, #7c3aed); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
  .header h1 { font-size: 20px; font-weight: 600; }
  .header small { color: #7d8590; font-size: 13px; margin-left: auto; }
  .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
  .card { background: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 20px; }
  .card-label { font-size: 12px; color: #7d8590; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
  .card-value { font-size: 32px; font-weight: 700; }
  .card-value.green { color: #3fb950; }
  .card-value.blue { color: #58a6ff; }
  .card-value.purple { color: #a371f7; }
  .card-value.red { color: #f85149; }
  .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }
  .status-badge.running { background: #1a3a2a; color: #3fb950; }
  .status-badge.stopped { background: #3a1a1a; color: #f85149; }
  .status-badge.reconnecting { background: #3a2e1a; color: #d29922; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .section-title { font-size: 14px; font-weight: 600; color: #7d8590; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
  .logs-box { background: #0d1117; border: 1px solid #21262d; border-radius: 12px; padding: 16px; max-height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.6; }
  .log-line { padding: 2px 0; border-bottom: 1px solid #161b22; }
  .log-line:last-child { border: none; }
  .nivel-success { color: #3fb950; }
  .nivel-error { color: #f85149; }
  .nivel-warning { color: #d29922; }
  .nivel-info { color: #58a6ff; }
  .config-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 32px; }
  .config-item { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; }
  .config-key { font-size: 13px; color: #7d8590; }
  .config-val { font-size: 13px; font-weight: 500; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .tag.on { background: #1a3a2a; color: #3fb950; }
  .tag.off { background: #21262d; color: #7d8590; }
</style>
</head>
<body>
<div class="header">
  <div class="logo">🤖</div>
  <h1>BlueBot</h1>
  <small>Atualiza a cada 10s • {{ now }}</small>
</div>
<div class="container">

  <!-- Status + Stats -->
  <div class="cards">
    <div class="card">
      <div class="card-label">Status</div>
      <div class="card-value" style="font-size:16px; margin-top:4px;">
        <span class="status-badge {{ stats.status }}">
          <span class="dot"></span>
          {{ stats.status | upper }}
        </span>
      </div>
    </div>
    <div class="card">
      <div class="card-label">Processadas hoje</div>
      <div class="card-value blue">{{ stats.today_processed }}</div>
    </div>
    <div class="card">
      <div class="card-label">Enviadas Telegram</div>
      <div class="card-value green">{{ stats.today_telegram }}</div>
    </div>
    <div class="card">
      <div class="card-label">Enviadas WhatsApp</div>
      <div class="card-value purple">{{ stats.today_whatsapp }}</div>
    </div>
    <div class="card">
      <div class="card-label">Erros 24h</div>
      <div class="card-value red">{{ stats.errors_24h }}</div>
    </div>
  </div>

  <!-- Config -->
  <div class="section-title" style="margin-bottom:12px;">Configuração ativa</div>
  <div class="config-grid" style="margin-bottom:32px;">
    <div class="config-item"><span class="config-key">Fonte</span><span class="config-val">{{ config.source }}</span></div>
    <div class="config-item"><span class="config-key">Destino</span><span class="config-val">{{ config.destination }}</span></div>
    <div class="config-item"><span class="config-key">Telegram</span><span class="tag {{ 'on' if config.telegram else 'off' }}">{{ 'ON' if config.telegram else 'OFF' }}</span></div>
    <div class="config-item"><span class="config-key">WhatsApp</span><span class="tag {{ 'on' if config.whatsapp else 'off' }}">{{ 'ON' if config.whatsapp else 'OFF' }}</span></div>
    <div class="config-item"><span class="config-key">Shopee</span><span class="tag {{ 'on' if config.shopee else 'off' }}">{{ 'ON' if config.shopee else 'OFF' }}</span></div>
    <div class="config-item"><span class="config-key">AliExpress</span><span class="tag {{ 'on' if config.ali else 'off' }}">{{ 'ON' if config.ali else 'OFF' }}</span></div>
    <div class="config-item"><span class="config-key">Mercado Livre</span><span class="tag {{ 'on' if config.ml else 'off' }}">{{ 'ON' if config.ml else 'OFF' }}</span></div>
    <div class="config-item"><span class="config-key">Delay</span><span class="config-val">{{ config.delay }}s</span></div>
  </div>

  <!-- Logs -->
  <div class="section-title">Logs recentes</div>
  <div class="logs-box">
    {% for entry in logs %}
    <div class="log-line">
      <span style="color:#7d8590">[{{ entry.horario }}]</span>
      <span class="nivel-{{ entry.nivel }}"> [{{ entry.nivel | upper }}]</span>
      {{ entry.mensagem }}
    </div>
    {% else %}
    <div style="color:#7d8590">Sem logs ainda...</div>
    {% endfor %}
  </div>

</div>
</body>
</html>
"""


def _start_panel(runner, config: dict) -> None:
    """Inicia o painel Flask em 0.0.0.0:8080."""
    app = Flask(__name__)

    @app.get("/")
    def dashboard():
        stats = runner.get_stats() if runner else {}
        stats["status"] = runner.status() if runner else "stopped"
        with _lock:
            logs_list = list(reversed(list(_logs)))
        now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        cfg = {
            "source": ", ".join(config.get("sources", [])),
            "destination": config.get("destination_telegram", "-"),
            "telegram": config.get("send_telegram", False),
            "whatsapp": config.get("send_whatsapp", False),
            "shopee": config.get("conv_shopee", False),
            "ali": config.get("conv_ali", False),
            "ml": config.get("conv_ml", False),
            "delay": config.get("delay_segundos", 3),
        }
        return render_template_string(DASHBOARD_HTML, stats=stats, logs=logs_list, config=cfg, now=now)

    @app.get("/api/status")
    def api_status():
        stats = runner.get_stats() if runner else {}
        stats["status"] = runner.status() if runner else "stopped"
        return jsonify(stats)

    @app.get("/api/logs")
    def api_logs():
        with _lock:
            return jsonify(list(_logs))

    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


def main():
    config = _load_config()

    if not config.get("api_id") or not config.get("api_hash"):
        log("error", "API_ID ou API_HASH não configurados no .env. Encerrando.")
        sys.exit(1)

    if not config.get("sources"):
        log("error", "SOURCE não configurado no .env. Encerrando.")
        sys.exit(1)

    log("info", "Iniciando BlueBot na VPS (modo pessoal)...")
    log("info", f"Fontes: {config['sources']}")
    log("info", f"Telegram: {'✅' if config['send_telegram'] else '❌'} | WhatsApp: {'✅' if config['send_whatsapp'] else '❌'}")
    log("info", "Painel disponível em http://0.0.0.0:8080")

    from bot_runner import BotRunner
    runner = BotRunner(log_callback=log)

    def _shutdown(*_):
        log("info", "Sinal de encerramento recebido. Parando bot...")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    runner.start(config)

    # Painel Flask em thread separada
    panel_thread = threading.Thread(target=_start_panel, args=(runner, config), daemon=True)
    panel_thread.start()

    # Mantém o processo vivo
    threading.Event().wait()


if __name__ == "__main__":
    main()
