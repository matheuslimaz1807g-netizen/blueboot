"""
affiliates/aliexpress.py — AliExpress affiliate link generation via official API.

Uses async httpx for non-blocking requests.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import Optional

import httpx

from utils import expandir_link_async


ALI_API_URL = "https://api-sg.aliexpress.com/sync"


def _extract_product_id(url: str) -> Optional[str]:
    for pattern in [
        r"productIds=(\d+)",
        r"/item/(\d+)\.html",
        r"(\d{8,})",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _sign(params: dict, secret: str) -> str:
    sign_str = secret + "".join(f"{k}{v}" for k, v in sorted(params.items())) + secret
    return hashlib.md5(sign_str.encode()).hexdigest().upper()


async def convert(
    links: list[str],
    app_key: str,
    app_secret: str,
    tracking_id: str,
) -> list[Optional[str]]:
    """
    Convert a list of AliExpress product URLs to affiliate links.
    Returns a same-length list; entries are None for failures.
    """
    results: list[Optional[str]] = []

    async with httpx.AsyncClient(timeout=15) as client:
        for link in links:
            # Expand shortened links
            if "a.aliexpress.com" in link or len(link) < 80:
                expanded = await expandir_link_async(link)
            else:
                expanded = link

            product_id = _extract_product_id(expanded)
            if not product_id:
                results.append(None)
                continue

            product_url = f"https://www.aliexpress.com/item/{product_id}.html"

            params: dict = {
                "method": "aliexpress.affiliate.link.generate",
                "app_key": app_key,
                "timestamp": str(int(time.time() * 1000)),
                "format": "json",
                "sign_method": "md5",
                "promotion_link_type": "0",
                "source_values": product_url,
                "tracking_id": tracking_id,
            }
            params["sign"] = _sign(params, app_secret)

            try:
                resp = await client.get(ALI_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                promo_list = (
                    data.get("aliexpress_affiliate_link_generate_response", {})
                    .get("resp_result", {})
                    .get("result", {})
                    .get("promotion_links", {})
                    .get("promotion_link", [])
                )
                if promo_list:
                    results.append(promo_list[0].get("promotion_link"))
                else:
                    results.append(None)
            except Exception:
                results.append(None)

    return results
