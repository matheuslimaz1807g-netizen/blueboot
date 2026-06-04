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

from affiliates import aliexpress, amazon, mercadolivre, shopee
from offer_filter import should_post
from utils import expandir_link_async
from shortener import shorten_url

# ── Text patterns ─────────────────────────────────────────────────────────────

_ANY_URL_PATTERN = re.compile(r"(https?://[^\s]+)")

_ML_PATTERN     = re.compile(r"(?:mercadolivre\.com(?:\.br)?|meli\.la)")
_ALI_PATTERN    = re.compile(r"(?:aliexpress\.com|a\.aliexpress\.com)")
_SHOPEE_PATTERN = re.compile(r"(?:shopee\.com\.br|s\.shopee\.com\.br)")
_AMZ_PATTERN    = re.compile(r"(?:amazon\.com(?:\.br)?|amzn\.to)")

_PRICE_PATTERN  = re.compile(r'R\$\s*([\d.,]+)', re.I)
_COUPON_PATTERN = re.compile(r'(?:cupom|codigo|coupon):\s*([A-Z0-9]+)', re.I)


# ── Text cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Apply text cleaning using the local text_cleaner module.
    """
    from text_cleaner import clean_offer_text
    return clean_offer_text(text)


# ── Promotion data extraction ─────────────────────────────────────────────────

def extract_promotion_data(
    raw_text: str,
    cleaned_text: str,
    image_path: Optional[str],
    expanded_map: dict,
    converted_links: dict,
    offer=None,
) -> Optional[dict]:
    lines = cleaned_text.splitlines()
    if not lines:
        return None

    originalTitle = raw_text.strip()
    seoTitle      = lines[0].strip()

    prices   = _PRICE_PATTERN.findall(cleaned_text)
    oldPrice = prices[0] if len(prices) > 1 else None
    newPrice = prices[-1] if prices else None

    coupon_match = _COUPON_PATTERN.search(cleaned_text)
    couponCode   = coupon_match.group(1) if coupon_match else None

    store = None
    for link in expanded_map.values():
        if _ML_PATTERN.search(link):
            store = "Mercado Livre"; break
        elif _ALI_PATTERN.search(link):
            store = "AliExpress"; break
        elif _SHOPEE_PATTERN.search(link):
            store = "Shopee"; break
        elif _AMZ_PATTERN.search(link):
            store = "Amazon"; break

    affiliateLink = list(converted_links.values())[0] if converted_links else None

    imageUrl = "https://via.placeholder.com/400x300?text=Imagem+da+Promocao"
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                encoded  = base64.b64encode(f.read()).decode()
                imageUrl = f"data:image/jpeg;base64,{encoded}"
        except Exception:
            pass

    return {
        "originalTitle": originalTitle,
        "seoTitle":      seoTitle,
        "oldPrice":      oldPrice,
        "newPrice":      newPrice,
        "couponCode":    couponCode,
        "imageUrl":      imageUrl,
        "store":         store,
        "affiliateLink": affiliateLink,
        "telegramLink":  None,
        # ── Análise de Negócio (populado em processar_mensagem) ──────────
        "offerScore":    None,
        "offerDecision": None,
        "offerCategory": None,
        "offerBrand":    None,
        "offerPosted":   True,
        "rejectReason":  None,
    }


def _score_decision(score: int) -> dict:
    """Classifica o score segundo a escala de negócio definida."""
    if score >= 70:
        return {"label": "Postar imediatamente", "tier": "hot", "emoji": "🔥"}
    elif score >= 50:
        return {"label": "Boa oferta", "tier": "good", "emoji": "✅"}
    elif score >= 38:
        return {"label": "Postar se houver espaço", "tier": "ok", "emoji": "📌"}
    elif score >= 20:
        return {"label": "Rejeitada", "tier": "reject", "emoji": "❌"}
    else:
        return {"label": "Rejeitada", "tier": "reject", "emoji": "❌"}


def _build_rejected_promo(offer) -> dict:
    """Constrói um promo dict mínimo para ofertas rejeitadas exibirem no dashboard."""
    decision = _score_decision(offer.score)
    return {
        "originalTitle": offer.raw_text[:80] if offer.raw_text else "Oferta rejeitada",
        "seoTitle":      "Oferta rejeitada pelo filtro",
        "oldPrice":      None,
        "newPrice":      None,
        "couponCode":    None,
        "imageUrl":      None,
        "store":         None,
        "affiliateLink": None,
        "telegramLink":  None,
        "offerScore":    offer.score,
        "offerDecision": decision,
        "offerCategory": offer.category,
        "offerBrand":    offer.brand,
        "offerPosted":   False,
        "rejectReason":  offer.reject_reason,
    }


def _sanitize_detected_url(url: str) -> str:
    return url.strip().strip("`'\"()[]{}<>.,;!")


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def processar_mensagem(
    msg,
    config: dict,
    telegram_client,
    log_callback: Callable[[str, str], None],
) -> tuple[bool, bool, bool, Optional[dict]]:
    msg_id: object = getattr(msg, "id", "?")
    image_path: Optional[str] = None

    try:
        # ── Step 1: Normalize unicode ─────────────────────────────────────────
        raw_text: str = unicodedata.normalize("NFKD", msg.raw_text or "")
        if not raw_text.strip():
            log_callback("info", f"[{msg_id}] Mensagem sem texto — ignorada.")
            return False, False, False, None

        should_publish, offer = should_post(raw_text, config.get("offer_filter", {}))
        if not should_publish:
            log_callback(
                "info",
                f"[{msg_id}] Oferta filtrada: {offer.reject_reason} "
                f"| score={offer.score}/100 | cat={offer.category}",
            )
            return True, False, False, _build_rejected_promo(offer)

        preview = " ".join(raw_text.splitlines()[:3]).strip()
        if len(preview) > 180:
            preview = preview[:177] + "..."
        log_callback("info", f"[{msg_id}] Processando mensagem. Preview: {preview}")

        # ── Step 2: Expand all URLs ───────────────────────────────────────────
        raw_urls     = _ANY_URL_PATTERN.findall(raw_text)
        expanded_map: dict[str, str] = {}
        for r_url in raw_urls:
            sanitized = _sanitize_detected_url(r_url)
            if sanitized not in expanded_map:
                try:
                    expanded_map[sanitized] = await expandir_link_async(sanitized)
                except Exception:
                    expanded_map[sanitized] = sanitized

        text = raw_text
        converted_links: dict[str, str] = {}
        any_link_converted = False
        store_name = ""

        # ── Step 2a: Mercado Livre ────────────────────────────────────────────
        if config.get("conv_ml"):
            for original_link, expanded_link in expanded_map.items():
                if _ML_PATTERN.search(expanded_link):
                    log_callback("info", f"[{msg_id}] Link ML detectado: {expanded_link}")
                    try:
                        aff = await mercadolivre.convert(expanded_link, config.get("ml_token", ""))
                        if aff and aff != expanded_link:
                            text = text.replace(original_link, aff)
                            converted_links[original_link] = aff
                            any_link_converted = True
                            store_name = "Mercado Livre"
                            log_callback("info", f"[{msg_id}] Link ML convertido.")
                        else:
                            log_callback("warning", f"[{msg_id}] Link ML não convertido. Usando original.")
                    except Exception as exc:
                        log_callback("error", f"[{msg_id}] Erro ML: {exc}. Usando original.")
        else:
            log_callback("info", f"[{msg_id}] Conversão Mercado Livre desativada.")

        # ── Step 2b: AliExpress ───────────────────────────────────────────────
        ali_key      = config.get("ali_key")
        ali_secret   = config.get("ali_secret")
        ali_tracking = config.get("ali_tracking")

        if config.get("conv_ali") and ali_key and ali_secret and ali_tracking:
            ali_originals = [o for o, e in expanded_map.items() if _ALI_PATTERN.search(e)]
            if ali_originals:
                log_callback("info", f"[{msg_id}] Links AliExpress detectados: {len(ali_originals)}")
                try:
                    to_convert = [expanded_map[o] for o in ali_originals]
                    converted  = await aliexpress.convert(to_convert, ali_key, ali_secret, ali_tracking)
                    for orig, new in zip(ali_originals, converted):
                        if new:
                            text = text.replace(orig, new)
                            converted_links[orig] = new
                            any_link_converted = True
                            store_name = "AliExpress"
                    log_callback("info", f"[{msg_id}] Links AliExpress convertidos.")
                except Exception as exc:
                    log_callback("error", f"[{msg_id}] Erro AliExpress: {exc}")
        elif config.get("conv_ali"):
            log_callback("warning", f"[{msg_id}] Conversão AliExpress ativa, mas credenciais incompletas.")
        else:
            log_callback("info", f"[{msg_id}] Conversão AliExpress desativada.")

        # ── Step 2c: Shopee ───────────────────────────────────────────────────
        shopee_app_id = config.get("shopee_app_id", "")
        shopee_secret = config.get("shopee_secret", "")
        
        # Retrocompatibilidade com shopee_token
        shopee_token = config.get("shopee_token", "")
        if not shopee_app_id and shopee_token:
            if ":" in shopee_token:
                shopee_app_id, shopee_secret = shopee_token.split(":", 1)
            else:
                shopee_app_id = shopee_token

        if config.get("conv_shopee") and shopee_app_id and shopee_secret:
            for original_link, expanded_link in expanded_map.items():
                if _SHOPEE_PATTERN.search(expanded_link):
                    log_callback("info", f"[{msg_id}] Link Shopee detectado: {expanded_link}")
                    try:
                        aff = await shopee.convert(
                            expanded_link,
                            app_id=shopee_app_id,
                            secret=shopee_secret,
                        )
                        if aff and aff != expanded_link:
                            text = text.replace(original_link, aff)
                            converted_links[original_link] = aff
                            any_link_converted = True
                            store_name = "Shopee"
                            log_callback("info", f"[{msg_id}] Link Shopee convertido.")
                        else:
                            log_callback("warning", f"[{msg_id}] Link Shopee não convertido. Usando original.")
                    except Exception as exc:
                        log_callback("error", f"[{msg_id}] Erro Shopee: {exc}")
        elif config.get("conv_shopee") and not (shopee_app_id and shopee_secret):
            log_callback("warning", f"[{msg_id}] Conversão Shopee ativa, mas shopee_app_id/shopee_secret ausentes.")
        else:
            log_callback("info", f"[{msg_id}] Conversão Shopee desativada.")

        # ── Step 2d: Amazon ───────────────────────────────────────────────────
        if config.get("conv_amz"):
            for original_link, expanded_link in expanded_map.items():
                if _AMZ_PATTERN.search(expanded_link):
                    log_callback("info", f"[{msg_id}] Link Amazon detectado: {expanded_link}")
                    try:
                        aff = await amazon.convert(
                            expanded_link,
                            amz_cookies=config.get("amz_cookies", ""),
                        )
                        if aff and aff != expanded_link:
                            text = text.replace(original_link, aff)
                            converted_links[original_link] = aff
                            any_link_converted = True
                            store_name = "Amazon"
                            log_callback("info", f"[{msg_id}] Link Amazon convertido.")
                        else:
                            log_callback("warning", f"[{msg_id}] Link Amazon não convertido. Usando original.")
                    except Exception as exc:
                        log_callback("error", f"[{msg_id}] Erro Amazon: {exc}. Usando original.")
        else:
            log_callback("info", f"[{msg_id}] Conversão Amazon desativada.")

        # ── Strict mode: abort if nothing was converted ───────────────────────
        if not any_link_converted:
            log_callback("warning", f"[{msg_id}] Nenhum link convertido. Mensagem ignorada.")
            return False, False, False, None

        # ── Keyword filter ────────────────────────────────────────────────────
        keywords: list[str] = config.get("filtros", {}).get("keywords", [])
        if any(kw.lower() in text.lower() for kw in keywords if kw):
            log_callback("info", f"[{msg_id}] Filtrada por palavra-chave.")
            return True, False, False, None

        # ── Step 3: Clean text & Inject Link ──────────────────────────────────
        # Applica a curadoria inteligente (text_cleaner.py)
        cleaned_text = clean_text(text)
        
        urgency_tag = ""
        if offer:
            if offer.is_price_drop:
                urgency_tag = f"🚨 CAIU MAIS! De R$ {offer.previous_price:.2f} por R$ {offer.price_now:.2f}\n"
            elif offer.score >= 70:
                urgency_tag = "🔥 IMPERDÍVEL / ESTOQUE LIMITADO\n"
            elif offer.score >= 50:
                urgency_tag = "⚡ PREÇO EXCELENTE\n"
        
        if any_link_converted:
            main_converted_link = next(iter(converted_links.values()))
            # Remove qualquer link original que sobrou no texto limpo
            cleaned_text_no_url = _ANY_URL_PATTERN.sub("", cleaned_text).strip()
            
            bitly_token = config.get("bitly_token", "")
            shortened_link = await shorten_url(main_converted_link, bitly_token)
            
            store_msg = f"🛒 Compre na {store_name}" if store_name else "🛒 Compre agora"
            text = f"{urgency_tag}{cleaned_text_no_url}\n\n{store_msg}:\n{shortened_link}"
            
            log_callback("info", f"[{msg_id}] Texto limpo e link encurtado.")
        else:
            text = f"{urgency_tag}{cleaned_text}"
            log_callback("info", f"[{msg_id}] Texto limpo (padrão sem conversão).")

        # ── Step 4: Download media ────────────────────────────────────────────
        if msg.media and isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument)):
            try:
                image_path = f"temp_{msg_id}.jpg"
                await msg.download_media(file=image_path)
                log_callback("info", f"[{msg_id}] Mídia baixada.")
            except Exception as exc:
                log_callback("error", f"[{msg_id}] Erro ao baixar mídia: {exc}")
                image_path = None

        # ── Step 4.5: Send promotion data to web API ──────────────────────────
        promotion_data = extract_promotion_data(raw_text, text, image_path, expanded_map, converted_links, offer)
        
        # Enriquece promo com dados de análise de negócio do offer_filter
        if promotion_data and offer:
            decision = _score_decision(offer.score)
            promotion_data["offerScore"]    = offer.score
            promotion_data["offerDecision"] = decision
            promotion_data["offerCategory"] = offer.category
            promotion_data["offerBrand"]    = offer.brand
            promotion_data["offerPosted"]   = True
            promotion_data["rejectReason"]  = None
        if promotion_data and config.get("send_to_web_api", True):
            web_api_url = config.get("web_api_url", "http://localhost:3000/api/promotions")
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(web_api_url, json=promotion_data)
                    if resp.status_code == 200:
                        log_callback("info", f"[{msg_id}] Promoção enviada para API web.")
                    else:
                        log_callback("warning", f"[{msg_id}] Erro API web: {resp.status_code} — {resp.text}")
            except Exception as exc:
                log_callback("error", f"[{msg_id}] Falha na API web: {exc}")

        # ── Step 5: Send to Telegram ──────────────────────────────────────────
        tg_sent         = False
        raw_destination = config.get("destination_telegram")

        if config.get("send_telegram"):
            if raw_destination:
                destinations = [d.strip() for d in raw_destination.split(",") if d.strip()]
                for dest in destinations:
                    try:
                        dest_entity = await telegram_client.get_entity(dest)
                        if image_path and os.path.exists(image_path):
                            sent_msg = await telegram_client.send_file(
                                dest_entity, file=image_path, caption=text, force_document=False
                            )
                        else:
                            sent_msg = await telegram_client.send_message(dest_entity, text, link_preview=False)
                            
                        # ── Quebra de Padrão (Humanização) ────────────────────
                        import random
                        # 1. Reações aleatórias para prova social (30% de chance)
                        if sent_msg and random.random() < 0.3:
                            try:
                                from telethon.tl.functions.messages import SendReactionRequest
                                from telethon.tl.types import ReactionEmoji
                                await telegram_client(SendReactionRequest(
                                    peer=dest_entity,
                                    msg_id=sent_msg.id,
                                    reaction=[ReactionEmoji(emoticon=random.choice(["🔥", "❤️", "👍", "👀", "👏"]))]
                                ))
                            except Exception:
                                pass
                                
                        # 2. Mensagem de engajamento fantasma (1 em 20 envios)
                        if random.randint(1, 20) == 1:
                            eng_texts = [
                                "Fiquem de olho nas mensagens com sirene 🚨, são os maiores descontos da semana!",
                                "Vocês viram que a Amazon tá com frete grátis na madruga hoje? Fiquem ligados aqui.",
                                "Lembrando galera: qualquer dúvida sobre as ofertas, podem avisar os admins."
                            ]
                            await telegram_client.send_message(dest_entity, random.choice(eng_texts))

                        log_callback("success", f"[{msg_id}] Enviado para Telegram: {dest}.")
                        tg_sent = True
                    except Exception as exc:
                        log_callback("error", f"[{msg_id}] Erro Telegram ({dest}): {exc}")
            else:
                log_callback("warning", f"[{msg_id}] Envio Telegram ativo, mas destino vazio.")
        else:
            log_callback("info", f"[{msg_id}] Envio para Telegram desativado.")

        # ── Step 6: Send to WhatsApp ──────────────────────────────────────────
        wp_sent          = False
        wpp_destinations = config.get("wpp_destinations", [])
        raw_endpoint     = config.get("whatsapp_endpoint") or "http://localhost:4000/send"
        wpp_endpoint     = raw_endpoint if raw_endpoint.endswith("/send") else f"{raw_endpoint.rstrip('/')}/send"

        targets_display = [
            f"Canal({d.replace('channel:', '')})" if d.startswith("channel:") else
            f"Grupo({d.replace('group:', '')})"   if d.startswith("group:")   else d
            for d in wpp_destinations
        ]

        log_callback(
            "info",
            f"[{msg_id}] [WhatsApp] ENABLED={config.get('send_whatsapp')} | "
            f"Endpoint={wpp_endpoint} | Destinos={', '.join(targets_display)}",
        )

        if config.get("send_whatsapp"):
            if isinstance(wpp_destinations, list) and wpp_destinations:
                payload: dict = {"text": text, "targets": wpp_destinations}
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        payload["base64Image"] = base64.b64encode(f.read()).decode()
                        payload["mimeType"]    = "image/jpeg"
                    log_callback("info", f"[{msg_id}] [WhatsApp] Enviando com imagem ({os.path.getsize(image_path)} bytes).")
                else:
                    log_callback("info", f"[{msg_id}] [WhatsApp] Enviando apenas texto.")

                try:
                    async with httpx.AsyncClient(timeout=300) as client:
                        resp = await client.post(wpp_endpoint, json=payload)
                        resp.raise_for_status()
                    log_callback("success", f"[{msg_id}] Enviado para WhatsApp com sucesso.")
                    wp_sent = True
                except httpx.HTTPStatusError as exc:
                    try:
                        err_detail = exc.response.json().get("error", exc.response.text)
                    except Exception:
                        err_detail = exc.response.text
                    log_callback("error", f"[{msg_id}] Erro WhatsApp ({exc.response.status_code}): {err_detail}")
                except Exception as exc:
                    log_callback("error", f"[{msg_id}] Erro ao conectar no WhatsApp: {exc}")

            elif not isinstance(wpp_destinations, list):
                log_callback("error", f"[{msg_id}] wpp_destinations não é lista! Tipo: {type(wpp_destinations)}")
            else:
                log_callback("warning", f"[{msg_id}] Envio WhatsApp ativo, mas lista de destinos vazia.")
        else:
            log_callback("info", f"[{msg_id}] Envio para WhatsApp desativado.")

        return True, tg_sent, wp_sent, promotion_data

    except Exception as exc:
        log_callback("error", f"[{msg_id}] Erro inesperado no pipeline: {exc}")
        return False, False, False, None

    finally:
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass
