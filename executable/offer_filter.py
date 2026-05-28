"""
offer_filter.py - Intelligent offer filtering with local SQLite persistence.

Call `should_post(raw_text, config)` before expensive link conversion/sending.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "max_posts_per_day": 10,
    "max_per_category_day": 3,
    "min_score": 40,
    "min_discount_pct": 30,
    "max_price": 500,
    "min_price": 15,
    "peak_hours": [7, 8, 9, 12, 13, 18, 19, 20, 21],
    "db_path": str(Path("data") / "offer_filter.sqlite3"),
}

CATEGORIES: dict[str, dict[str, Any]] = {
    "eletronicos": {
        "emojis": ["🔋", "📱", "💻", "🖥", "⌨", "🖱", "📷", "🎧", "🔌", "📡"],
        "keywords": [
            "carregador", "power bank", "fone", "notebook", "celular",
            "tablet", "smartwatch", "cabo", "adaptador", "roteador",
            "headphone", "earphone", "monitor", "teclado", "mouse",
            "ssd", "memoria", "memória", "pen drive", "hub", "bateria",
            "bluetooth", "usb", "logitech",
        ],
        "score_bonus": 10,
    },
    "moda": {
        "emojis": ["👟", "👕", "👖", "🧦", "👗", "👜", "🧢", "👒", "👠"],
        "keywords": [
            "tenis", "tênis", "camiseta", "calca", "calça", "meia",
            "vestido", "blusa", "jaqueta", "moletom", "shorts",
            "sandalia", "sandália", "chinelo", "kit", "conjunto",
        ],
        "score_bonus": 8,
    },
    "casa": {
        "emojis": ["🏠", "🍲", "🧹", "🛋", "🪣", "🧺", "🪴", "🛁", "🚿"],
        "keywords": [
            "pote", "panela", "frigideira", "organizador", "rack",
            "estante", "tapete", "toalha", "lencol", "lençol",
            "travesseiro", "secador", "aspirador", "liquidificador",
            "airfryer", "fritadeira", "cafeteira", "chaleira", "ferro",
            "ventilador",
        ],
        "score_bonus": 7,
    },
    "saude_beleza": {
        "emojis": ["💊", "💪", "🧴", "💆", "🧼", "🪥"],
        "keywords": [
            "cafeina", "cafeína", "creatina", "whey", "suplemento",
            "vitamina", "proteina", "proteína", "colageno", "colágeno",
            "omega", "ômega", "capsulas", "cápsulas", "shampoo",
            "condicionador", "perfume", "creme", "protetor", "esmalte",
        ],
        "score_bonus": 9,
    },
    "ferramentas": {
        "emojis": ["🔧", "🪛", "⚙️", "🔨", "🪚"],
        "keywords": [
            "furadeira", "parafusadeira", "esmerilhadeira", "chave",
            "alicate", "fita", "nivel", "nível", "trena",
            "kit ferramentas",
        ],
        "score_bonus": 6,
    },
    "outros": {"emojis": [], "keywords": [], "score_bonus": 0},
}

TRUSTED_BRANDS = [
    "puma", "nike", "adidas", "kappa", "samsung", "xiaomi", "jbl",
    "anker", "logitech", "britania", "britânia", "mondial", "philips",
    "multilaser", "intelbras", "bosch", "makita", "dux", "growth",
    "optimum", "nestle", "tramontina", "fischer",
]

_PRICE_RE = re.compile(r"r\$\s*([\d.,]+)", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


@dataclass
class Offer:
    raw_text: str
    price_now: Optional[float] = None
    price_original: Optional[float] = None
    discount_pct: Optional[float] = None
    has_coupon: bool = False
    has_free_shipping: bool = False
    has_pix: bool = False
    has_installment: bool = False
    brand: Optional[str] = None
    category: str = "outros"
    score: int = 0
    reject_reason: Optional[str] = None
    fingerprint: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def should_post(raw_text: str, config: Optional[dict[str, Any]] = None) -> tuple[bool, Offer]:
    cfg = _resolve_config(config)
    offer = _parse_offer(raw_text)
    offer.score = _score_offer(offer, cfg)
    offer.fingerprint = _product_fingerprint(raw_text)

    if not cfg["enabled"]:
        return True, offer

    _init_db(cfg["db_path"])

    if _fingerprint_seen_today(cfg["db_path"], offer.fingerprint):
        offer.reject_reason = "duplicata"
        _record_offer(cfg["db_path"], offer, approved=False)
        return False, offer

    approved = _evaluate_rules(offer, cfg)
    _record_offer(cfg["db_path"], offer, approved=approved)
    return approved, offer


def daily_status(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = _resolve_config(config)
    today = str(date.today())

    if not Path(cfg["db_path"]).exists():
        return _empty_status(today, cfg)

    _init_db(cfg["db_path"])
    with sqlite3.connect(cfg["db_path"]) as conn:
        total = conn.execute(
            """
            SELECT COUNT(*) FROM offer_filter_events
            WHERE day = ? AND approved = 1
            """,
            (today,),
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT category, COUNT(*) FROM offer_filter_events
            WHERE day = ? AND approved = 1
            GROUP BY category
            """,
            (today,),
        ).fetchall()

    by_category = {category: count for category, count in rows}
    return {
        "data": today,
        "postados_hoje": total,
        "limite_diario": cfg["max_posts_per_day"],
        "restantes": max(0, cfg["max_posts_per_day"] - total),
        "por_categoria": by_category,
    }


def _resolve_config(config: Optional[dict[str, Any]]) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    source = config or {}
    nested = source.get("offer_filter") if isinstance(source.get("offer_filter"), dict) else {}

    for key in cfg:
        env_key = f"OFFER_FILTER_{key.upper()}"
        if env_key in os.environ:
            cfg[key] = _coerce_env_value(os.environ[env_key], cfg[key])

    for key, value in nested.items():
        if value is not None:
            cfg[key] = value

    for key, value in source.items():
        if key in cfg and value is not None:
            cfg[key] = value

    cfg["enabled"] = bool(cfg["enabled"])
    cfg["max_posts_per_day"] = int(cfg["max_posts_per_day"])
    cfg["max_per_category_day"] = int(cfg["max_per_category_day"])
    cfg["min_score"] = int(cfg["min_score"])
    cfg["min_discount_pct"] = float(cfg["min_discount_pct"])
    cfg["max_price"] = float(cfg["max_price"])
    cfg["min_price"] = float(cfg["min_price"])
    cfg["peak_hours"] = [int(hour) for hour in cfg.get("peak_hours", [])]
    cfg["db_path"] = str(cfg["db_path"])
    return cfg


def _coerce_env_value(value: str, default: Any) -> Any:
    if isinstance(default, bool):
        return value.strip().lower() in {"1", "true", "yes", "sim", "on"}
    if isinstance(default, int):
        return int(value)
    if isinstance(default, float):
        return float(value.replace(",", "."))
    if isinstance(default, list):
        return [int(v.strip()) for v in value.split(",") if v.strip()]
    return value


def _parse_offer(raw_text: str) -> Offer:
    offer = Offer(raw_text=raw_text)
    text_lower = raw_text.lower()

    offer.price_now, offer.price_original = _extract_prices(raw_text)
    if offer.price_now and offer.price_original and offer.price_original > offer.price_now:
        offer.discount_pct = round((1 - offer.price_now / offer.price_original) * 100, 1)

    offer.has_coupon = bool(re.search(r"\b(cupom|coupon|codigo|c[oó]digo)\b", text_lower))
    offer.has_free_shipping = bool(re.search(r"frete\s*(gratis|gr[aá]tis|free)", text_lower))
    offer.has_pix = bool(re.search(r"\bpix\b", text_lower))
    offer.has_installment = bool(re.search(r"\d+x\s*(?:de\s*)?r\$|\bparcel", text_lower))
    offer.category = _detect_category(raw_text)
    offer.brand = _detect_brand(raw_text)
    return offer


def _extract_prices(text: str) -> tuple[Optional[float], Optional[float]]:
    text_lower = text.lower()
    de_por = re.search(
        r"de[:\s]*r\$\s*([\d.,]+).*?(?:por|agora)[:\s]*r\$\s*([\d.,]+)",
        text_lower,
        re.DOTALL,
    )
    if de_por:
        original = _parse_brl(de_por.group(1))
        now = _parse_brl(de_por.group(2))
        return now, original

    parsed = [_parse_brl(value) for value in _PRICE_RE.findall(text_lower)]
    prices = sorted({price for price in parsed if price is not None})
    if len(prices) >= 2:
        return prices[0], prices[-1]
    if len(prices) == 1:
        return prices[0], None
    return None, None


def _parse_brl(value: str) -> Optional[float]:
    try:
        clean = value.strip()
        if "," in clean:
            clean = clean.replace(".", "").replace(",", ".")
        return float(clean)
    except (TypeError, ValueError):
        return None


def _detect_category(text: str) -> str:
    normalized = _normalize_text(text)
    for category, data in CATEGORIES.items():
        if category == "outros":
            continue
        if any(emoji in text for emoji in data["emojis"]):
            return category
        if any(_normalize_text(keyword) in normalized for keyword in data["keywords"]):
            return category
    return "outros"


def _detect_brand(text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    for brand in TRUSTED_BRANDS:
        if _normalize_text(brand) in normalized:
            return brand
    return None


def _is_premium_item(text: str) -> bool:
    """Verifica se o texto contém palavras-chave de produtos premium de alta conversão."""
    premium_keywords = [
        "iphone", "tv", "smart tv", "notebook", "macbook", 
        "galaxy s", "playstation", "ps5", "xbox"
    ]
    normalized = _normalize_text(text)
    return any(_normalize_text(kw) in normalized for kw in premium_keywords)


def _score_offer(offer: Offer, cfg: dict[str, Any]) -> int:
    score = 0

    if offer.discount_pct is not None:
        if offer.discount_pct >= 70:
            score += 35
        elif offer.discount_pct >= 60:
            score += 28
        elif offer.discount_pct >= 50:
            score += 22
        elif offer.discount_pct >= 40:
            score += 15
        elif offer.discount_pct >= 30:
            score += 8
        else:
            score += 2
    else:
        score += 5

    if offer.has_coupon:
        score += 10
    if offer.has_pix:
        score += 8
    if offer.has_free_shipping:
        score += 7

    if offer.price_now:
        if 20 <= offer.price_now <= 150:
            score += 15
        elif 150 < offer.price_now <= 300:
            score += 10
        elif 300 < offer.price_now <= 500:
            score += 5
        elif offer.price_now < 20:
            score += 3

    score += CATEGORIES.get(offer.category, CATEGORIES["outros"])["score_bonus"]

    if offer.brand:
        score += 10

    if datetime.now().hour in cfg["peak_hours"]:
        score += 5

    return min(score, 100)


def _evaluate_rules(offer: Offer, cfg: dict[str, Any]) -> bool:
    if offer.price_now is not None:
        is_premium = _is_premium_item(offer.raw_text)
        # Itens premium ignoram o max_price normal e tem um limite muito maior
        effective_max_price = 15000 if is_premium else cfg["max_price"]

        if offer.price_now > effective_max_price:
            offer.reject_reason = f"preco muito alto (R${offer.price_now:.2f}) e nao premium"
            return False
        if offer.price_now < cfg["min_price"]:
            offer.reject_reason = f"preco muito baixo (R${offer.price_now:.2f})"
            return False

    if offer.discount_pct is not None and offer.discount_pct < cfg["min_discount_pct"]:
        offer.reject_reason = f"desconto baixo ({offer.discount_pct:.1f}%)"
        return False

    if offer.score < cfg["min_score"]:
        offer.reject_reason = f"score baixo ({offer.score}/100)"
        return False

    status = daily_status(cfg)
    if status["postados_hoje"] >= cfg["max_posts_per_day"]:
        offer.reject_reason = f"limite diario atingido ({cfg['max_posts_per_day']}/dia)"
        return False

    category_count = status.get("por_categoria", {}).get(offer.category, 0)
    if category_count >= cfg["max_per_category_day"]:
        offer.reject_reason = (
            f"limite de categoria ({offer.category}: "
            f"{category_count}/{cfg['max_per_category_day']})"
        )
        return False

    return True


def _init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offer_filter_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                created_at TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                approved INTEGER NOT NULL,
                category TEXT NOT NULL,
                score INTEGER NOT NULL,
                reject_reason TEXT,
                price_now REAL,
                price_original REAL,
                discount_pct REAL,
                brand TEXT,
                metadata_json TEXT NOT NULL,
                raw_text TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_offer_filter_day_approved
            ON offer_filter_events(day, approved)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_offer_filter_day_fingerprint
            ON offer_filter_events(day, fingerprint)
            """
        )


def _fingerprint_seen_today(db_path: str, fingerprint: str) -> bool:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT 1 FROM offer_filter_events
            WHERE day = ? AND fingerprint = ?
            LIMIT 1
            """,
            (str(date.today()), fingerprint),
        ).fetchone()
    return row is not None


def _record_offer(db_path: str, offer: Offer, approved: bool) -> None:
    metadata = offer.to_dict()
    metadata.pop("raw_text", None)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO offer_filter_events (
                day, created_at, fingerprint, approved, category, score,
                reject_reason, price_now, price_original, discount_pct,
                brand, metadata_json, raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(date.today()),
                offer.timestamp,
                offer.fingerprint,
                1 if approved else 0,
                offer.category,
                offer.score,
                offer.reject_reason,
                offer.price_now,
                offer.price_original,
                offer.discount_pct,
                offer.brand,
                json.dumps(metadata, ensure_ascii=False),
                offer.raw_text,
            ),
        )


def _product_fingerprint(text: str) -> str:
    no_urls = _URL_RE.sub(" ", text)
    normalized = _normalize_text(no_urls)
    words = re.findall(r"[a-z0-9]+", normalized)
    compact = " ".join(words[:16])
    prices = [str(_parse_brl(value)) for value in _PRICE_RE.findall(text) if _parse_brl(value)]
    source = "|".join([compact, prices[-1] if prices else ""])
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _normalize_text(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", text or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def _empty_status(today: str, cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": today,
        "postados_hoje": 0,
        "limite_diario": cfg["max_posts_per_day"],
        "restantes": cfg["max_posts_per_day"],
        "por_categoria": {},
    }
