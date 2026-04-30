"""
config_loader.py — Fetches bot configuration from the remote API.

All credentials are downloaded at startup and kept in memory only.
Nothing sensitive is written to disk.
"""
from __future__ import annotations

import os
import urllib3
from typing import Optional

import requests

# Suppress SSL warnings for self-signed certificates (local dev/testing)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_API_BASE_DEFAULT: str = "https://api.yourdomain.com"
REQUEST_TIMEOUT: int = 15


def get_api_base() -> str:
    """Return API_BASE from environment, falling back to compiled default."""
    return os.environ.get("APRO_API_BASE", _API_BASE_DEFAULT)


class ConfigLoadError(Exception):
    pass


def fetch_config(license_key: str, machine_id: str) -> dict:
    """
    GET /config/{license_key}?machine_id={machine_id}

    Returns the full decrypted config dict including affiliate credentials.
    Raises ConfigLoadError if request fails or server returns non-2xx.
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
            raise ConfigLoadError(
                "Configuração ainda não definida. Acesse o painel e salve suas configurações."
            )
        raise ConfigLoadError(f"Erro ao carregar configurações: {exc}")
    except requests.RequestException as exc:
        raise ConfigLoadError(f"Sem conexão com o servidor de configurações: {exc}")


def push_config(license_key: str, machine_id: str, config: dict) -> dict:
    """
    PUT /config/{license_key}?machine_id={machine_id}

    Pushes updated config to the remote API. Returns the saved config.
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
        raise ConfigLoadError(f"Erro ao salvar configurações: {exc}")
