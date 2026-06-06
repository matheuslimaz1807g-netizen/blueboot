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
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


TZ_BR = timezone(timedelta(hours=-3))


def _get_today_br() -> str:
    return datetime.now(TZ_BR).strftime("%Y-%m-%d")


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "max_posts_per_day": 15,
    "max_per_category_day": 3,
    "min_score": 40,
    "min_discount_pct": 30,
    "max_price": 500,
    "min_price": 15,
    "peak_hours": [7, 8, 9, 12, 13, 18, 19, 20, 21],
    "db_path": str(Path("data") / "offer_filter.sqlite3"),
    "min_score_bypass_limit": 70,
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
    "optimum", "nestle", "tramontina", "fischer", "mizuno", "asics",
    "fila", "olympikus", "under armour", "umbro"
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
    has_official_store: bool = False
    brand: Optional[str] = None
    category: str = "outros"
    score: int = 0
    reject_reason: Optional[str] = None
    fingerprint: str = ""
    is_price_drop: bool = False
    previous_price: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(TZ_BR).isoformat())

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
        prev_price = _get_previous_price(cfg["db_path"], offer.fingerprint)
        if prev_price is not None and offer.price_now is not None and offer.price_now < prev_price:
            offer.is_price_drop = True
            offer.previous_price = prev_price
        else:
            offer.reject_reason = "duplicata"
            _record_offer(cfg["db_path"], offer, approved=False)
            return False, offer

    approved = _evaluate_rules(offer, cfg)
    _record_offer(cfg["db_path"], offer, approved=approved)
    return approved, offer


def daily_status(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = _resolve_config(config)
    today = _get_today_br()

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
    cfg["min_score_bypass_limit"] = int(cfg.get("min_score_bypass_limit", 70))
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

    offer.has_coupon = bool(re.search(r"\b(cupom|cupons|coupon|coupons|codigo|c[oó]digo)s?\b", text_lower))
    offer.has_free_shipping = bool(re.search(r"frete\s*(gratis|gr[aá]tis|free)", text_lower))
    offer.has_pix = bool(re.search(r"\bpix\b", text_lower))
    offer.has_installment = bool(re.search(r"\b\d+x\b|\bparcel", text_lower))
    offer.has_official_store = bool(re.search(r"\bloja oficial\b", text_lower))
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
    """
    Análise de Negócio Sênior.

    Escala de decisão:
      70-100 → Postar imediatamente
      50-69  → Postar (boa oferta)
      38-49  → Postar se houver espaço no dia
      20-37  → Rejeitar
      0-19   → Rejeitar
    """
    score = 0

    # ── 1. Marca reconhecida ou Loja Oficial (+20/+15) ───────────────────
    # Aumenta conversão independente do desconto mostrado.
    if offer.brand:
        score += 20
        
    if offer.has_official_store:
        score += 15

    # ── 2. Categoria de demanda contínua (+15) ────────────────────────────
    # Higiene, suplemento, casa: vende sempre, qualquer dia.
    CONTINUOUS_DEMAND = {"saude_beleza", "casa", "eletronicos"}
    if offer.category in CONTINUOUS_DEMAND:
        score += 15
    else:
        # Outras categorias com bônus menor
        score += CATEGORIES.get(offer.category, CATEGORIES["outros"])["score_bonus"]

    # ── 3. Ticket entre R$15 e R$200: impulso, alta conversão (+20) ────────
    if offer.price_now:
        if 15 <= offer.price_now <= 200:
            score += 20  # Zona de impulso puro
        elif 200 < offer.price_now <= 500:
            score += 12  # Consideração moderada
        elif 500 < offer.price_now <= 1500:
            score += 6   # Ticket alto = comissão alta, mas menor conversão
        elif offer.price_now > 1500:
            score += 10  # Premium: comissão alta compensa
        elif offer.price_now < 15:
            score += 2   # Muito barato, margem pequena
    else:
        # Ausência de preço (ex: ML sem "De/Por") não é rejeição
        score += 5

    # ── 4. Desconto explícito (bônus adicional, mas não obrigatório) ───────
    if offer.discount_pct is not None:
        if offer.discount_pct >= 70:
            score += 20
        elif offer.discount_pct >= 60:
            score += 15
        elif offer.discount_pct >= 50:
            score += 12
        elif offer.discount_pct >= 40:
            score += 8
        elif offer.discount_pct >= 30:
            score += 4
        elif offer.discount_pct > 0:
            score += 1
        # desconto zero ou negativo: 0 bônus

    # ── 5. Múltiplos benefícios combinados (+bônus acumulado) ──────────────
    # Cupom + pix + loja oficial juntos valem muito.
    benefit_count = sum([
        offer.has_coupon,
        offer.has_pix,
        offer.has_free_shipping,
        offer.has_installment,
    ])
    if benefit_count >= 3:
        score += 15  # Combo poderoso
    elif benefit_count == 2:
        score += 8
    elif benefit_count == 1:
        score += 4

    # ── 6. Horário de pico (+5) ─────────────────────────────────────────────
    if datetime.now(TZ_BR).hour in cfg["peak_hours"]:
        score += 5

    return min(score, 100)


def _evaluate_rules(offer: Offer, cfg: dict[str, Any]) -> bool:
    # Preço: só rejeita se o preço existir E for claramente errado.
    if offer.price_now is not None:
        is_premium = _is_premium_item(offer.raw_text)
        effective_max_price = 15000 if is_premium else cfg["max_price"]

        if offer.price_now > effective_max_price:
            offer.reject_reason = f"preço acima do limite (R${offer.price_now:.2f})"
            return False
        if offer.price_now < cfg["min_price"]:
            offer.reject_reason = f"preço muito baixo (R${offer.price_now:.2f})"
            return False

    # Desconto baixo isolado NÃO é motivo de rejeição (spec sênior).
    # Só rejeita se também não houver nenhum outro diferencial (brand, categoria, benefícios).
    if (offer.discount_pct is not None
            and offer.discount_pct < cfg["min_discount_pct"]
            and not offer.brand
            and offer.category == "outros"
            and not offer.has_coupon
            and not offer.has_pix
            and not offer.has_free_shipping):
        offer.reject_reason = f"sem diferencial: desconto baixo ({offer.discount_pct:.1f}%) e sem marca/cupom/benefício"
        return False

    # Score mínimo: alinhado com escala sênior (38 = postar se houver espaço)
    min_score = cfg.get("min_score", 38)
    if offer.score < min_score:
        offer.reject_reason = f"score insuficiente ({offer.score}/100, mínimo: {min_score})"
        return False

    status = daily_status(cfg)
    bypass_limit = offer.score >= cfg.get("min_score_bypass_limit", 70)

    if not bypass_limit:
        if status["postados_hoje"] >= cfg["max_posts_per_day"]:
            offer.reject_reason = f"limite diário atingido ({cfg['max_posts_per_day']}/dia)"
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
        cursor = conn.execute(
            """
            SELECT 1 FROM offer_filter_events
            WHERE day = ? AND fingerprint = ? AND approved = 1
            LIMIT 1
            """,
            (_get_today_br(), fingerprint),
        )
        return cursor.fetchone() is not None

def _get_previous_price(db_path: str, fingerprint: str) -> Optional[float]:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT price_now FROM offer_filter_events
            WHERE day = ? AND fingerprint = ? AND approved = 1
            ORDER BY id DESC LIMIT 1
            """,
            (_get_today_br(), fingerprint),
        )
        row = cursor.fetchone()
        return row[0] if row else None


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
                _get_today_br(),
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
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


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
