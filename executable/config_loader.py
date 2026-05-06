"""
config_loader.py — Gerenciador de configurações do BlueBot.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_API_BASE_DEFAULT: str = "https://api.bluebot.com.br"
REQUEST_TIMEOUT: int = 15


class ConfigLoadError(Exception):
    pass


def get_api_base() -> str:
    return os.environ.get("APRO_API_BASE", _API_BASE_DEFAULT)


def load_config_from_env() -> dict:
    """
    Carrega as configurações. 
    Prioriza variáveis já definidas no sistema (Docker) e usa .env apenas como fallback.
    """
    # Se já temos API_ID no ambiente (via Docker env_file), não sobrescrevemos com arquivos locais
    if not os.getenv("API_ID"):
        # Padronizado: .env.local (específico) -> .env (base)
        for f in [".env.local", ".env"]:
            if Path(f).exists():
                print(f"[ConfigLoader] Carregando arquivo de ambiente: {f}", flush=True)
                load_dotenv(dotenv_path=f, override=False)

    config = {
        "api_id": os.getenv("API_ID", ""),
        "api_hash": os.getenv("API_HASH", ""),
        "phone": os.getenv("TELEGRAM_PHONE", ""),
        "session_string": os.getenv("TELEGRAM_SESSION_STRING", ""),
        "sources": [s.strip() for s in os.getenv("SOURCE", "").split(",") if s.strip()],
        "destination_telegram": os.getenv("DESTINATION", ""),
        "delay_segundos": int(os.getenv("DELAY", "3")),
        "wpp_destinations": [s.strip() for s in os.getenv("WHATSAPP_DESTINATIONS", "").split(",") if s.strip()],
        "whatsapp_endpoint": os.getenv("WHATSAPP_ENDPOINT", "http://localhost:4000/send") or "http://localhost:4000/send",
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
    
    # Debug log (sanitized)
    print(f"[ConfigLoader] Config Local: WPP={config['send_whatsapp']} | Destinos={len(config['wpp_destinations'])} | Endpoint={config['whatsapp_endpoint']}", flush=True)
    
    return config


def merge_configs(local: dict, remote: dict) -> dict:
    """
    Mescla a configuração local com a remota.
    Valores remotos têm prioridade, a menos que sejam nulos, vazios ou 'None' string.
    """
    merged = local.copy()
    for k, v in remote.items():
        # Ignora se o valor for nulo, string "None" ou vazio para campos críticos
        if v is None or v == "None" or v == "":
            continue
            
        # Se for lista vazia e temos algo local, mantém o local
        if isinstance(v, list) and not v:
            if merged.get(k):
                continue
                
        # Caso especial para endpoint: se a API retornar algo que não começa com http, ignoramos
        if k == "whatsapp_endpoint" and isinstance(v, str) and not v.startswith("http"):
            continue

        merged[k] = v
        
    print(f"[ConfigLoader] Config Mesclada: WPP={merged.get('send_whatsapp')} | Destinos={len(merged.get('wpp_destinations', []))} | Endpoint={merged.get('whatsapp_endpoint')}", flush=True)
    return merged


def fetch_remote_config(license_key: str, machine_id: str) -> dict:
    try:
        resp = requests.get(
            f"{get_api_base()}/config/{license_key}",
            params={"machine_id": machine_id},
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise ConfigLoadError(f"Erro ao carregar config remota: {exc}")


def push_remote_config(license_key: str, machine_id: str, config: dict) -> dict:
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
    except Exception as exc:
        raise ConfigLoadError(f"Erro ao salvar config remota: {exc}")
