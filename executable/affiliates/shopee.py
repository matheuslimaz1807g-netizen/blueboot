"""
affiliates/shopee.py — Shopee affiliate link generation.

Autenticação idêntica ao script bash de referência:
  FACTOR = APPID + TIMESTAMP + PAYLOAD + SECRET
  SIGNATURE = SHA256(FACTOR)
  Header: Authorization: SHA256 Credential={APPID}, Timestamp={TIMESTAMP}, Signature={SIGNATURE}
"""
from __future__ import annotations

import hashlib
import json
import time

import httpx

from utils import expandir_link_async

_SHOPEE_API = "https://open-api.affiliate.shopee.com.br/graphql"

_GQL_MUTATION = (
    'mutation { generateShortLink(input:{ '
    'originUrl:"%s", '
    'subIds:["s1","s2","s3","s4","s5"] '
    '}) { shortLink } }'
)


def _build_signature(app_id: str, timestamp: int, payload: str, secret: str) -> str:
    """Replica exata do bash: SHA256(APPID + TIMESTAMP + PAYLOAD + SECRET)."""
    factor = f"{app_id}{timestamp}{payload}{secret}"
    return hashlib.sha256(factor.encode("utf-8")).hexdigest()


def _build_payload(url: str) -> str:
    """Monta o JSON do body GraphQL com a URL do produto."""
    query = _GQL_MUTATION % url
    return json.dumps({"query": query})


async def convert(original_link: str, app_id: str = "", secret: str = "") -> str:
    """
    Gera um shortlink de afiliado Shopee oficial.

    Parâmetros
    ----------
    original_link : URL do produto (encurtada ou completa).
    app_id        : APPID da conta de afiliado Shopee.
    secret        : SECRET correspondente ao APPID.

    Retorna o shortlink gerado ou o link original em caso de falha.
    """
    if not app_id or not secret:
        return original_link

    # Expande links curtos (s.shopee.com.br ou similares)
    is_short = "s.shopee.com.br" in original_link or len(original_link) < 80
    expanded = await expandir_link_async(original_link) if is_short else original_link

    payload   = _build_payload(expanded)
    timestamp = int(time.time())
    signature = _build_signature(app_id, timestamp, payload, secret)

    headers = {
        "Authorization": (
            f"SHA256 Credential={app_id}, "
            f"Timestamp={timestamp}, "
            f"Signature={signature}"
        ),
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(_SHOPEE_API, headers=headers, content=payload)
            r.raise_for_status()
            data      = r.json()
            shortlink = data.get("data", {}).get("generateShortLink", {}).get("shortLink")
            if shortlink:
                return shortlink
    except Exception as exc:
        # Loga mas não quebra o fluxo — retorna o link expandido como fallback
        print(f"[Shopee] Falha ao gerar shortlink: {exc}", flush=True)

    return expanded