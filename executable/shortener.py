import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def shorten_url(url: str, bitly_token: Optional[str] = None) -> str:
    """
    Encurta a URL usando Bitly (se token for fornecido) ou TinyURL como fallback.
    """
    if bitly_token:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {
                    "Authorization": f"Bearer {bitly_token}",
                    "Content-Type": "application/json"
                }
                payload = {"long_url": url, "domain": "bit.ly"}
                resp = await client.post("https://api-ssl.bitly.com/v4/shorten", json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    return resp.json().get("link", url)
                else:
                    logger.warning(f"Erro no Bitly ({resp.status_code}): {resp.text}. Usando TinyURL como fallback.")
        except Exception as e:
            logger.warning(f"Exceção no Bitly: {e}. Usando TinyURL como fallback.")

    # Fallback para TinyURL (grátis, sem token)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"https://tinyurl.com/api-create.php?url={url}")
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        logger.warning(f"Erro ao encurtar com TinyURL: {e}. Mantendo link original.")

    return url
