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
    Expande URLs encurtadas (ex: amzn.to, a.aliexpress.com) seguindo redirecionamentos.
    Utiliza httpx assíncrono.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        try:
            r = await client.get(url)
            return str(r.url)
        except Exception:
            return url
