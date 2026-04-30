"""
affiliates/shopee.py — Shopee affiliate link generation.

Expands shortened URLs then injects tracking parameters.
No Selenium required — pure HTTP.
"""
from __future__ import annotations

import random
import string
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx


async def expand_url(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        resp = await client.get(url)
        return str(resp.url)


def _inject_params(url: str) -> str:
    parsed = urlparse(url)
    base = parsed._replace(query="").geturl()

    # Strip old affiliate/tracking params
    params = {
        k: v
        for k, v in parse_qsl(parsed.query)
        if not any(kw in k for kw in ("utm_", "uls_", "track", "affiliate", "ref"))
    }

    rand_chars = string.ascii_lowercase + string.digits
    tracking_id = "bluebot" + "".join(random.choices(rand_chars, k=8))
    campaign_id = "apenaspromo" + "".join(random.choices(rand_chars, k=6))
    term_id = "bot" + "".join(random.choices(rand_chars, k=10))

    params.update({
        "uls_trackid": tracking_id,
        "utm_campaign": campaign_id,
        "utm_content": "----",
        "utm_medium": "affiliates",
        "utm_source": "",
        "utm_term": term_id,
    })

    return base + "?" + urlencode(params)


async def _shorten(url: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post("https://tinyurl.com/api-create.php", params={"url": url})
            if r.status_code == 200 and r.text.startswith("http"):
                return r.text
        except Exception:
            pass

        try:
            r = await client.post(
                "https://is.gd/create.php", params={"format": "simple", "url": url}
            )
            if r.status_code == 200 and r.text.startswith("http"):
                return r.text
        except Exception:
            pass

    return url


async def convert(original_link: str) -> str:
    """Generate a Shopee affiliate link from a product or shortened URL."""
    is_short = "s.shopee.com.br" in original_link or len(original_link) < 80

    if is_short:
        expanded = await expand_url(original_link)
    else:
        expanded = original_link

    with_params = _inject_params(expanded)
    return await _shorten(with_params)
