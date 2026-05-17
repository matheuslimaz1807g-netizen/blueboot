"""
pipeline.py — Full message processing pipeline.

Designed to be compiled with Cython before packaging to protect the
business logic and affiliate injection from reverse engineering.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
import unicodedata
from typing import Callable, Optional

import httpx
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from affiliates import aliexpress, mercadolivre, shopee
from utils import expandir_link_async

# ── Text patterns ─────────────────────────────────────────────────────────────

_ANY_URL_PATTERN = re.compile(
    r"(https?://[^\s]+)"
)

_ML_PATTERN = re.compile(
    r"(?:mercadolivre\.com(?:\.br)?|meli\.la)"
)
_ALI_PATTERN = re.compile(
    r"(?:aliexpress\.com|a\.aliexpress\.com)"
)
_SHOPEE_PATTERN = re.compile(
    r"(?:shopee\.com\.br|s\.shopee\.com\.br)"
)

_PRICE_PATTERN = re.compile(r'R\$\s*([\d.,]+)', re.I)
_COUPON_PATTERN = re.compile(r'(?:cupom|codigo|coupon):\s*([A-Z0-9]+)', re.I)


# ── Text cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Apply the exact cleaning rules defined in the spec:
    1. Remove the first non-empty line (headline from the source group)
    2. Remove all lines that start with '#'
    3. Remove duplicate empty lines
    4. Insert a blank line after the first remaining line (product title)
    """
    lines = text.splitlines()

    # Step 1: skip the first non-empty line (the "headline")
    i = 0
    for i, line in enumerate(lines):
        if line.strip():
            i += 1
            break

    # Skip blank lines immediately after the headline
    while i < len(lines) and not lines[i].strip():
        i += 1

    remaining = lines[i:]

    # Step 2: remove hashtag lines
    remaining = [ln for ln in remaining if not ln.strip().startswith("#")]

    # Step 3 + 4: collapse multiple blanks and insert one blank after first line
    result: list[str] = []
    blank_count = 0
    for idx, ln in enumerate(remaining):
        if not ln.strip():
            blank_count += 1
            if blank_count == 1:
                result.append("")
        else:
            blank_count = 0
            result.append(ln)
            if idx == 0 and len(remaining) > 1:
                # Insert blank after the product title
                result.append("")

    return "\n".join(result).strip()


# ── Promotion data extraction ─────────────────────────────────────────────────

def extract_promotion_data(raw_text: str, cleaned_text: str, image_path: Optional[str], expanded_map: dict, converted_links: dict) -> Optional[dict]:
    """
    Extract promotion data from message text for web API.
    """
    lines = cleaned_text.splitlines()
    if not lines:
        return None

    originalTitle = raw_text.strip()
    seoTitle = lines[0].strip()

    # Extract prices
    prices = _PRICE_PATTERN.findall(cleaned_text)
    oldPrice = prices[0] if len(prices) > 1 else None
    newPrice = prices[-1] if prices else None

    # Extract coupon
    coupon_match = _COUPON_PATTERN.search(cleaned_text)
    couponCode = coupon_match.group(1) if coupon_match else None

    # Determine store
    store = None
    for link in expanded_map.values():
        if _ML_PATTERN.search(link):
            store = "Mercado Livre"
            break
        elif _ALI_PATTERN.search(link):
            store = "AliExpress"
            break
        elif _SHOPEE_PATTERN.search(link):
            store = "Shopee"
            break

    # Affiliate link (first converted)
    affiliateLink = list(converted_links.values())[0] if converted_links else None

    # Image URL
    imageUrl = None
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
                encoded = base64.b64encode(image_data).decode()
                imageUrl = f"data:image/jpeg;base64,{encoded}"
        except Exception:
            imageUrl = "https://via.placeholder.com/400x300?text=Imagem+da+Promocao"
    else:
        imageUrl = "https://via.placeholder.com/400x300?text=Imagem+da+Promocao"

    # Telegram link (placeholder)
    telegramLink = None  # To be set later if needed

    return {
        "originalTitle": originalTitle,
        "seoTitle": seoTitle,
        "oldPrice": oldPrice,
        "newPrice": newPrice,
        "couponCode": couponCode,
        "imageUrl": imageUrl,
        "store": store,
        "affiliateLink": affiliateLink,
        "telegramLink": telegramLink,
    }

# Removido _expand_link local, importado de utils.py

def _sanitize_detected_url(url: str) -> str:
    """Remove wrappers commonly used in Telegram formatting around URLs."""
    return url.strip().strip("`'\"()[]{}<>.,;!")


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def processar_mensagem(
    msg,
    config: dict,
    telegram_client,
    log_callback: Callable[[str, str], None],
) -> bool:
    """
    Execute the full processing pipeline for a single Telegram message.

    Args:
        msg: Telethon Message object
        config: Decrypted config dict from config_loader
        telegram_client: Active TelegramClient instance
        log_callback: Callable(nivel: str, mensagem: str) — "info"|"success"|"error"

    Returns:
        True if the message was fully delivered, False on failure.
    """
    msg_id = getattr(msg, "id", "?")
    image_path: Optional[str] = None

    try:
        # ── Step 1: Normalize unicode ─────────────────────────────────────────
        raw_text: str = unicodedata.normalize("NFKD", msg.raw_text or "")
        if not raw_text.strip():
            log_callback("info", f"[{msg_id}] Mensagem sem texto — ignorada.")
            return False, False, False

        preview = " ".join(raw_text.splitlines()[:3]).strip()
        if len(preview) > 180:
            preview = preview[:177] + "..."
        log_callback("info", f"[{msg_id}] Processando mensagem. Preview: {preview}")

        # ── Step 2: Convert affiliate links ───────────────────────────────────
        text = raw_text
        converted_links = {}

        # Flag to track if AT LEAST ONE link was successfully converted
        any_link_converted = False

        # 2. Extract and expand ALL urls to check their final destination
        raw_urls = _ANY_URL_PATTERN.findall(text)
        expanded_map = {}
        for r_url in raw_urls:
            sanitized = _sanitize_detected_url(r_url)
            if sanitized not in expanded_map:
                try:
                    exp = await expandir_link_async(sanitized)
                    expanded_map[sanitized] = exp
                except:
                    expanded_map[sanitized] = sanitized

        # 2a. Mercado Livre
        if config.get("conv_ml"):
            for original_link, expanded_link in expanded_map.items():
                if _ML_PATTERN.search(expanded_link):
                    log_callback("info", f"[{msg_id}] Link ML detectado após expansão: {expanded_link}")
                    try:
                        aff = await mercadolivre.convert(expanded_link, config.get("ml_token", ""))
                        if aff and aff != expanded_link:
                            text = text.replace(original_link, aff)
                            converted_links[original_link] = aff
                            log_callback("info", f"[{msg_id}] Link ML convertido via Navegador.")
                            any_link_converted = True
                        else:
                            log_callback("warning", f"[{msg_id}] Link ML nao convertido. Usando link original. URL: {expanded_link}")
                    except Exception as exc:
                        log_callback("error", f"[{msg_id}] Erro ML ao converter {expanded_link}: {exc}. Usando link original.")
        else:
            log_callback("info", f"[{msg_id}] Conversão Mercado Livre desativada.")

        # 2b. AliExpress
        ali_key = config.get("ali_key")
        ali_secret = config.get("ali_secret")
        ali_tracking = config.get("ali_tracking")
        if config.get("conv_ali") and ali_key and ali_secret and ali_tracking:
            ali_originals = []
            for original_link, expanded_link in expanded_map.items():
                if _ALI_PATTERN.search(expanded_link):
                    ali_originals.append(original_link)

            if ali_originals:
                log_callback("info", f"[{msg_id}] Links AliExpress detectados: {len(ali_originals)}")
                try:
                    # Passamos os originais ou os expandidos? A API do Ali geralmente prefere originais,
                    # mas se for encurtador externo, melhor mandar o expandido.
                    to_convert = [expanded_map[o] for o in ali_originals]
                    converted = await aliexpress.convert(to_convert, ali_key, ali_secret, ali_tracking)
                    for orig, new in zip(ali_originals, converted):
                        if new:
                            text = text.replace(orig, new)
                            converted_links[orig] = new
                            any_link_converted = True
                    log_callback("info", f"[{msg_id}] Links AliExpress convertidos.")
                except Exception as exc:
                    log_callback("error", f"[{msg_id}] Erro AliExpress: {exc}")
        elif config.get("conv_ali"):
            log_callback("warning", f"[{msg_id}] Conversão AliExpress ativa, mas credenciais incompletas.")
        else:
            log_callback("info", f"[{msg_id}] Conversão AliExpress desativada.")

        # 2c. Shopee
        if config.get("conv_shopee") and config.get("shopee_token"):
            for original_link, expanded_link in expanded_map.items():
                if _SHOPEE_PATTERN.search(expanded_link):
                    log_callback("info", f"[{msg_id}] Link Shopee detectado após expansão: {expanded_link}")
                    try:
                        aff = await shopee.convert(expanded_link)
                        if aff:
                            text = text.replace(original_link, aff)
                            converted_links[original_link] = aff
                            any_link_converted = True
                        log_callback("info", f"[{msg_id}] Link Shopee convertido.")
                    except Exception as exc:
                        log_callback("error", f"[{msg_id}] Erro Shopee: {exc}")
        elif config.get("conv_shopee"):
            log_callback("warning", f"[{msg_id}] Conversão Shopee ativa, mas token ausente.")
        else:
            log_callback("info", f"[{msg_id}] Conversão Shopee desativada.")

        # STRICT MODE: Abort if no links were converted
        if not any_link_converted:
            log_callback("warning", f"[{msg_id}] Nenhum link conhecido convertido (ex: Amazon/Magalu ou sem link). Mensagem ignorada.")
            return False, False, False

        # Apply keyword filters (ignore message if any keyword matches)
        keywords: list[str] = config.get("filtros", {}).get("keywords", [])
        if any(kw.lower() in text.lower() for kw in keywords if kw):
            log_callback("info", f"[{msg_id}] Filtrada por palavra-chave.")
            return True, False, False

        # ── Step 3: Clean text ────────────────────────────────────────────────
        text = clean_text(text)
        log_callback("info", f"[{msg_id}] Texto limpo.")

        # ── Step 4: Download media ────────────────────────────────────────────
        if msg.media and isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument)):
            try:
                image_path = f"temp_{msg_id}.jpg"
                await msg.download_media(file=image_path)
                log_callback("info", f"[{msg_id}] Mídia baixada.")
            except Exception as exc:
                log_callback("error", f"[{msg_id}] Erro ao baixar mídia: {exc}")
                image_path = None

        # ── Step 4.5: Extract promotion data and send to web API ────────────
        # FUTURE: multi-tenant: include tenant_id in webhook payload
        promotion_data = extract_promotion_data(raw_text, text, image_path, expanded_map, converted_links)
        if promotion_data and config.get("send_to_web_api", True):
            web_api_url = config.get("web_api_url", "http://localhost:3000/api/promotions")
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(web_api_url, json=promotion_data)
                    if resp.status_code == 200:
                        log_callback("info", f"[{msg_id}] Promoção enviada para API web.")
                    else:
                        log_callback("warning", f"[{msg_id}] Erro ao enviar para API web: {resp.status_code} - {resp.text}")
            except Exception as exc:
                log_callback("error", f"[{msg_id}] Falha na API web: {exc}")

        # ── Step 5: Send to Telegram ──────────────────────────────────────────
        tg_sent = False
        destination = config.get("destination_telegram")
        if config.get("send_telegram"):
            if destination:
                try:
                    dest_entity = await telegram_client.get_entity(destination)
                    if image_path and os.path.exists(image_path):
                        # Envia como arquivo local garantindo que não use os atributos da mídia original
                        await telegram_client.send_file(
                            dest_entity, 
                            file=image_path, 
                            caption=text,
                            force_document=False
                        )
                    else:
                        await telegram_client.send_message(
                            dest_entity, 
                            text, 
                            link_preview=False
                        )
                    log_callback("success", f"[{msg_id}] Enviado para Telegram.")
                    tg_sent = True
                except Exception as exc:
                    log_callback("error", f"[{msg_id}] Erro Telegram: {exc}")
            else:
                log_callback("warning", f"[{msg_id}] Envio Telegram ativo, mas destino vazio.")
        else:
            log_callback("info", f"[{msg_id}] Envio para Telegram desativado.")

        # ── Step 6: Send to WhatsApp ──────────────────────────────────────────
        wp_sent = False
        wpp_destinations = config.get("wpp_destinations", [])
        raw_endpoint = config.get("whatsapp_endpoint") or "http://localhost:4000/send"
        if not raw_endpoint.endswith("/send"):
            wpp_endpoint = f"{raw_endpoint.rstrip('/')}/send"
        else:
            wpp_endpoint = raw_endpoint
        
        # Log de debug para diagnosticar problemas
        log_callback("info", f"[{msg_id}] [WhatsApp Debug] ENABLE_WHATSAPP={config.get('send_whatsapp')} | Endpoint={wpp_endpoint} | Destinos={wpp_destinations} (tipo: {type(wpp_destinations)})")
        
        if config.get("send_whatsapp"):
            if isinstance(wpp_destinations, list) and len(wpp_destinations) > 0:
                payload: dict = {"text": text, "targets": wpp_destinations}
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        payload["base64Image"] = base64.b64encode(f.read()).decode()
                        payload["mimeType"] = "image/jpeg"
                    log_callback("info", f"[{msg_id}] [WhatsApp] Enviando com imagem ({os.path.getsize(image_path)} bytes).")
                else:
                    log_callback("info", f"[{msg_id}] [WhatsApp] Enviando apenas texto.")
                
                log_callback("info", f"[{msg_id}] [WhatsApp] POST para {wpp_endpoint} | Grupos: {', '.join(wpp_destinations)}")
                try:
                    async with httpx.AsyncClient(timeout=300) as client:
                        resp = await client.post(wpp_endpoint, json=payload)
                        resp.raise_for_status()
                    log_callback("success", f"[{msg_id}] ✅ Enviado para WhatsApp com sucesso.")
                    wp_sent = True
                except httpx.HTTPStatusError as exc:
                    try:
                        err_detail = exc.response.json().get("error", exc.response.text)
                    except:
                        err_detail = exc.response.text
                    log_callback("error", f"[{msg_id}] ❌ Erro WhatsApp ({exc.response.status_code}): {err_detail}")
                except Exception as exc:
                    log_callback("error", f"[{msg_id}] ❌ Erro ao conectar no WhatsApp: {exc}")
            elif not isinstance(wpp_destinations, list):
                log_callback("error", f"[{msg_id}] ❌ ERRO: wpp_destinations não é uma lista! Tipo: {type(wpp_destinations)} | Valor: {wpp_destinations}")
            else:
                log_callback("warning", f"[{msg_id}] ⚠️ Envio WhatsApp ativo, mas lista de destinos está vazia.")
        else:
            log_callback("info", f"[{msg_id}] ℹ️ Envio para WhatsApp DESATIVADO no config.")

        return True, tg_sent, wp_sent

    except Exception as exc:
        log_callback("error", f"[{msg_id}] Erro inesperado no pipeline: {exc}")
        return False, False, False

    finally:
        # ── Step 7: Cleanup temp file ─────────────────────────────────────────
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass
