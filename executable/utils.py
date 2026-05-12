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


def get_verify_ssl() -> bool:
    """
    Retorna se deve verificar SSL nas requisições HTTP.
    
    Comportamento:
    - Se SSL_VERIFY estiver definido como 'true'/'1': retorna True (produção)
    - Se SSL_VERIFY estiver definido como 'false'/'0': retorna False (dev/test)
    - Se não definido: retorna True (seguro por padrão)
    
    Para endpoints internos do Docker (ex: http://api:8000), a verificação
    é desabilitada automaticamente pois são URLs HTTP internas.
    """
    env_val = os.environ.get("SSL_VERIFY", "true").strip().lower()
    return env_val in ("true", "1", "yes")


def should_verify_ssl(url: str) -> bool:
    """
    Decide se deve verificar SSL para uma URL específica.
    
    URLs internas do Docker (http://) não precisam de verificação SSL.
    URLs externas (https://) verificam conforme configurado.
    """
    if url.startswith("http://"):
        return False
    return get_verify_ssl()


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
