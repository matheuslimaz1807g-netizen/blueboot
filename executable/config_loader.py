"""
config_loader.py — Gerenciador de configurações do BlueBot.

Suporta:
- Modo Local/Pessoal: Lê diretamente do arquivo .env.
- Modo Gerenciado: Busca configurações da API remota via chave de licença.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests
import urllib3
from dotenv import load_dotenv

# Ignora avisos de SSL para conexões locais/desenvolvimento
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_API_BASE_DEFAULT: str = "https://api.bluebot.com.br"
REQUEST_TIMEOUT: int = 15


class ConfigLoadError(Exception):
    pass


def get_api_base() -> str:
    return os.environ.get("APRO_API_BASE", _API_BASE_DEFAULT)


def load_config_from_env() -> dict:
    """
    Carrega as configurações a partir das variáveis de ambiente (.env).
    Utilizado no modo Pessoal/VPS sem painel centralizado.
    """
    # Garante que o .env seja lido
    load_dotenv(dotenv_path=".env", override=True)
    
    # Prioriza .env.local se existir
    if Path(".env.local").exists():
        load_dotenv(dotenv_path=".env.local", override=True)

    return {
        "api_id": os.getenv("API_ID", ""),
        "api_hash": os.getenv("API_HASH", ""),
        "phone": os.getenv("TELEGRAM_PHONE", ""),
        "session_string": os.getenv("TELEGRAM_SESSION_STRING", ""),
        "sources": [s.strip() for s in os.getenv("SOURCE", "").split(",") if s.strip()],
        "destination_telegram": os.getenv("DESTINATION", ""),
        "delay_segundos": int(os.getenv("DELAY", "3")),
        "wpp_destinations": [s.strip() for s in os.getenv("WHATSAPP_DESTINATIONS", "").split(",") if s.strip()],
        "whatsapp_endpoint": os.getenv("WHATSAPP_ENDPOINT", "http://localhost:4000/send"),
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
        "web_api_url": os.getenv("WEB_API_URL", "http://localhost:3000/api/promotions"),
        "send_to_web_api": os.getenv("SEND_TO_WEB_API", "true").lower() == "true",
    }


def fetch_remote_config(license_key: str, machine_id: str) -> dict:
    """
    Busca a configuração na API remota usando a licença.
    """
    try:
        resp = requests.get(
            f"{get_api_base()}/config/{license_key}",
            params={"machine_id": machine_id},
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise ConfigLoadError("Configuração não definida no painel remoto.")
        raise ConfigLoadError(f"Erro ao carregar config remota: {exc}")
    except requests.RequestException as exc:
        raise ConfigLoadError(f"Sem conexão com servidor de licenças: {exc}")


def push_remote_config(license_key: str, machine_id: str, config: dict) -> dict:
    """
    Envia a configuração local para o servidor remoto.
    """
    try:
        resp = requests.put(
            f"{get_api_base()}/config/{license_key}",
            params={"machine_id": machine_id},
            json=config,
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise ConfigLoadError(f"Erro ao salvar config remota: {exc}")
