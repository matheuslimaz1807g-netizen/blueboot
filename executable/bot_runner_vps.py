"""
bot_runner_vps.py — Entry point simplificado para rodar o bot na VPS (sem Flask, sem licença).

Lê tudo direto do .env e inicia o BotRunner continuamente.
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env
load_dotenv(dotenv_path=".env", override=True)

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


def log(nivel: str, mensagem: str) -> None:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [{nivel.upper()}] {mensagem}", flush=True)


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

    from bot_runner import BotRunner
    runner = BotRunner(log_callback=log)

    # Graceful shutdown com Ctrl+C / SIGTERM
    def _shutdown(*_):
        log("info", "Sinal de encerramento recebido. Parando bot...")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    runner.start(config)

    # Mantém o processo vivo enquanto o bot roda em segundo plano
    import threading
    threading.Event().wait()


if __name__ == "__main__":
    main()
