"""
utils.py — Funções utilitárias compartilhadas entre módulos.

Centraliza lógica comum para evitar duplicação de código.
"""
from __future__ import annotations

import os
import subprocess
import httpx


# FUTURE: multi-tenant utility methods
# def get_tenant_config(tenant_id: str) -> dict: ...


def fechar_brave() -> None:
    """
    Fecha o navegador Brave forçosamente.
    Implementação específica para Windows. No Linux (headless) não faz nada.
    """
    if os.name == 'nt':
        try:
            subprocess.call(
                ['taskkill', '/F', '/IM', 'brave.exe'],
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


async def expandir_link_async(url: str) -> str:
    """
    Expande URLs encurtadas (ex: amzn.to, a.aliexpress.com, meli.la) seguindo redirecionamentos.
    Utiliza httpx assíncrono com headers de navegador para evitar bloqueios (CloudFront, etc).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=headers) as client:
        try:
            r = await client.get(url)
            final_url = str(r.url)
            # Se conseguiu seguir os redirects e chegou numa URL diferente, retorna ela
            if final_url and final_url != url:
                return final_url
            return url
        except Exception:
            return url
