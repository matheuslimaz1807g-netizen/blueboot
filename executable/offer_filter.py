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
    "max_posts_per_day": 20,
    "max_per_category_day": 4,
    "min_score": 60,
    "min_discount_pct": 25,
    "max_price": 500,
    "min_price": 15,
    "peak_hours": [7, 8, 9, 12, 13, 18, 19, 20, 21],
    "db_path": str(Path("data") / "offer_filter.sqlite3"),

    # IMPORTANTE
    # Somente ofertas muito fortes ignoram os limites
    "min_score_bypass_limit": 80,

    # Anti-spam por janela de tempo
    # Mínimo de minutos entre posts aprovados consecutivos
    "min_interval_minutes": 10,
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
            # Termos de smartphones
            "smartphone", "iphone", "galaxy", "redmi", "poco",
            "motorola", "moto g", "moto e", "positivo twist",
        ],
        "score_bonus": 10,
    },
    "moda": {
        "emojis": ["👟", "👖", "🧦", "👗", "👜", "🧢", "👒", "👠", "🕶️", "👓", "🎒"],
        "keywords": [
            "tenis", "tênis", "camiseta", "calca", "calça", "meia",
            "vestido", "blusa", "jaqueta", "moletom", "shorts",
            "sandalia", "sandália", "chinelo", "conjunto",
            # Acessórios e bolsas — frequentemente enviados por canais de moda
            "bolsa", "mala", "mochila", "carteira", "clutch", "necessaire",
            "oculos", "óculos", "oculos de sol", "óculos de sol",
            "bone", "boné", "gorro", "cachecol", "luva", "cinto",
            "kit roupa", "pijama", "agasalho", "regata",
            "bermuda", "legging", "top",
        ],
        "score_bonus": 8,
    },
    "casa": {
        "emojis": ["🏠", "🍲", "🧹", "🛋", "🪣", "🧺", "🪴", "🛁", "🚿", "👕"],
        "keywords": [
            "pote", "panela", "frigideira", "organizador", "rack",
            "estante", "tapete", "toalha", "lencol", "lençol",
            "travesseiro", "secador", "aspirador", "liquidificador",
            "airfryer", "fritadeira", "cafeteira", "chaleira", "ferro",
            "ventilador", "varal", "cabide", "cesto", "vassoura",
            "rodo", "balde", "cortina", "persiana", "colchao", "colchão",
            "almofada", "edredom", "coberta", "cobertor",
        ],
        "score_bonus": 7,
    },

    "saude_beleza": {
        "emojis": ["💊", "💪", "🧴", "💆", "🧼", "🪥", "🫧"],
        "keywords": [
            "cafeina", "cafeína", "creatina", "whey", "suplemento",
            "vitamina", "proteina", "proteína", "colageno", "colágeno",
            "omega", "ômega", "capsulas", "cápsulas", "shampoo",
            "condicionador", "perfume", "creme", "protetor", "esmalte",
            # Itens de higiene e corpo
            "body splash", "body mist", "splash", "hidratante",
            "sabonete", "gel", "desodorante", "antitranspirante",
            "kit perfume", "kit beleza", "maquiagem", "batom",
            "loção", "locao", "serum", "sérum", "tônico", "tonico",
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

# Marcas confiáveis expandidas com marcas premium e de alta conversão
TRUSTED_BRANDS = [
    # Esportivo / Moda
    "puma", "nike", "adidas", "kappa", "mizuno", "asics",
    "fila", "olympikus", "under armour", "umbro", "vans", "all star",
    "converse", "new balance", "reebok", "oakley", "reserva",
    # Eletrônicos / Tecnologia
    "samsung", "xiaomi", "apple", "jbl", "anker", "logitech",
    "multilaser", "intelbras", "positivo", "lenovo", "dell",
    "hp", "acer", "asus", "kingston", "sandisk", "seagate",
    "western digital", "wd", "corsair", "redragon", "hyperx",
    # Eletrodomésticos / Casa
    "britania", "britânia", "mondial", "philips", "walita",
    "oster", "electrolux", "consul", "brastempe", "lg",
    "tramontina", "fischer", "tramontina", "rocker", "rochedo",
    "oxford", "santorini", "utilissima",
    # Ferramentas
    "bosch", "makita", "dewalt", "stanley", "skil", "vonder",
    # Beleza / Saúde
    "growth", "optimum", "nestle", "pantene", "elseve",
    "niely", "salon line", "loreal", "l'oreal",
    # Premium / Luxo
    "dyson", "sony", "bose", "marshall", "jbl", "apple",
    "galaxy", "iphone", "ipad", "macbook", "airpods",
    "playstation", "xbox", "nintendo", "steam",
]

# Palavras que sugerem produto genérico sem marca (baixa qualidade)
_GENERIC_KEYWORDS = [
    "generico", "genérico", "similar", "paralelo", "importado",
    "sem marca", "sem nome", "alternativo", "comum", "basico", "básico",
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
    cfg["min_score_bypass_limit"] = int(cfg.get("min_score_bypass_limit", 80))
    cfg["min_interval_minutes"] = int(cfg.get("min_interval_minutes", 10))
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
    offer.has_pix = bool(re.search(r"\bpix\b|\bà vista\b|\ba vista\b", text_lower))
    offer.has_installment = bool(re.search(r"\b\d+x\b|\bparcel", text_lower))
    offer.has_official_store = bool(re.search(r"\bloja oficial\b", text_lower))
    offer.category = _detect_category(raw_text)
    offer.brand = _detect_brand(raw_text)
    return offer


# Detecta preço sem R$: "por 59,41", "59,41 no pix", "por R$ 59,41"
_PRICE_NO_RS_RE = re.compile(
    r"(?:por|pagando|de)\s*([\d]{1,4}(?:[.,]\d{2})?)(?:\s*(?:no pix|à vista|a vista|reais))",
    re.IGNORECASE,
)


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
    # Tenta capturar preço sem R$ (ex: "59,41 no pix")
    if not parsed:
        match = _PRICE_NO_RS_RE.search(text_lower)
        if match:
            price = _parse_brl(match.group(1))
            if price:
                return price, None

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
    # Prioriza keywords sobre emojis (mais precisas; evita falsos positivos como 👕 em varal)
    for category, data in CATEGORIES.items():
        if category == "outros":
            continue
        if any(_normalize_text(keyword) in normalized for keyword in data["keywords"]):
            return category
    for category, data in CATEGORIES.items():
        if category == "outros":
            continue
        if any(emoji in text for emoji in data["emojis"]):
            return category
    return "outros"


def _detect_brand(text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    for brand in TRUSTED_BRANDS:
        if _normalize_text(brand) in normalized:
            return brand
    return None


def _is_generic_product(text: str) -> bool:
    """Detecta se o texto sugere produto genérico/sem marca."""
    normalized = _normalize_text(text)
    for keyword in _GENERIC_KEYWORDS:
        if _normalize_text(keyword) in normalized:
            return True
    return False


def _is_premium_item(text: str) -> bool:
    """Verifica se o texto contém palavras-chave de produtos premium de alta conversão."""
    premium_keywords = [
        "iphone", "tv", "smart tv", "notebook", "macbook",
        "galaxy s", "playstation", "ps5", "ps4", "xbox",
        "xbox series", "nintendo switch", "ipad", "airpods",
        "apple watch", "dyson", "oled", "4k", "ultra hd",
        "soundbar", "home theater", "apple", "mac",
    ]
    normalized = _normalize_text(text)
    return any(_normalize_text(kw) in normalized for kw in premium_keywords)


def _score_offer(offer: Offer, cfg: dict[str, Any]) -> int:
    """
    Sistema de pontuação rebalanceado para filtrar ofertas de baixa qualidade.

    Escala de decisão:
       80-100  → Postar imediatamente (ignora limites diários)
       70-79   → Postar (excelente oferta)
       60-69   → Postar (boa oferta, respeita limites)
       50-59   → Postar se houver diferencial forte e espaço
       < 60    → Rejeitar (padrão: min_score = 60)
    """
    score = 0

    # ── 1. Marca reconhecida (+20) ───────────────────────────────────────
    # Marcas fortes = alta conversão. Essencial para qualidade.
    if offer.brand:
        score += 20

    # ── 2. Loja oficial (+10) ────────────────────────────────────────────
    # Loja oficial passa mais credibilidade, mas é menos valiosa que marca
    if offer.has_official_store:
        score += 10

    # ── 3. Categorias prioritárias (+10) ─────────────────────────────────
    # eletronicos, casa, saude_beleza têm demanda constante e alta conversão
    PRIORITY_CATEGORIES = {"eletronicos", "casa", "saude_beleza"}
    if offer.category in PRIORITY_CATEGORIES:
        score += 10
    else:
        score += CATEGORIES.get(offer.category, CATEGORIES["outros"])["score_bonus"]

    # ── 4. Preço (bônus moderado — evita boost excessivo para produtos baratos) ─
    if offer.price_now:
        if 15 <= offer.price_now <= 200:
            score += 10   # Zona de impulso, bom para conversão
        elif 200 < offer.price_now <= 500:
            score += 8    # Consideração moderada
        elif 500 < offer.price_now <= 1500:
            score += 5    # Ticket alto, comissão boa
        elif offer.price_now > 1500:
            score += 8    # Premium: comissão alta compensa o volume menor
        # preço < 15: 0 pontos (margem insignificante)

    # ── 5. Desconto (PESO MAIOR — principal diferencial) ─────────────────
    if offer.discount_pct is not None:
        if offer.discount_pct >= 70:
            score += 30   # Oferta explosiva! Quase de graça
        elif offer.discount_pct >= 60:
            score += 25   # Desconto agressivo, baita oferta
        elif offer.discount_pct >= 50:
            score += 20   # Meio preço, chama atenção
        elif offer.discount_pct >= 40:
            score += 15   # Desconto significativo
        elif offer.discount_pct >= 30:
            score += 10   # Desconto razoável
        elif offer.discount_pct >= 20:
            score += 5    # Desconto mínimo relevante
        # abaixo de 20%: 0 pontos (desconto irrelevante)

    # ── 6. Múltiplos benefícios combinados ───────────────────────────────
    benefit_count = sum([
        offer.has_coupon,
        offer.has_pix,
        offer.has_free_shipping,
        offer.has_installment,
    ])
    if benefit_count >= 3:
        score += 10   # Combo poderoso: cupom + frete + pix
    elif benefit_count == 2:
        score += 5    # Dupla de benefícios
    elif benefit_count == 1:
        score += 2    # Benefício isolado

    # ── 7. Horário de pico (+3) ──────────────────────────────────────────
    if datetime.now(TZ_BR).hour in cfg["peak_hours"]:
        score += 3

    # ── 8. Bônus premium (+5) ────────────────────────────────────────────
    # Produtos de alto valor agregado (iPhone, Dyson, etc.)
    if _is_premium_item(offer.raw_text):
        score += 5

    # ── 9. Penalidade para produto genérico (-10) ────────────────────────
    # Produto claramente sem marca perde pontos
    if _is_generic_product(offer.raw_text):
        score -= 10

    # ── 10. Bônus price drop (+5) ────────────────────────────────────────
    # Oferta que já caiu de preço HOJE (redução adicional)
    if offer.is_price_drop:
        score += 5

    return max(min(score, 100), 0)


def _evaluate_rules(offer: Offer, cfg: dict[str, Any]) -> bool:
    """
    Avalia regras de aprovação/rejeição em ordem de prioridade.

    A ordem importa: regras mais específicas vêm primeiro.
    """

    # ── R1. Preço fora dos limites ──────────────────────────────────────
    if offer.price_now is not None:
        is_premium = _is_premium_item(offer.raw_text)
        effective_max_price = 15000 if is_premium else cfg["max_price"]

        if offer.price_now > effective_max_price:
            offer.reject_reason = f"preço acima do limite (R${offer.price_now:.2f})"
            return False
        if offer.price_now < cfg["min_price"]:
            offer.reject_reason = f"preço muito baixo (R${offer.price_now:.2f})"
            return False

    # ── R2. Sem diferencial → REJEITAR (regra universal) ────────────────
    # A oferta DEVE ter pelo menos UM dos seguintes diferenciais:
    #   • desconto >= 20%
    #   • cupom ativo
    #   • marca reconhecida
    #   • loja oficial
    has_decent_discount = offer.discount_pct is not None and offer.discount_pct >= 20
    if not (has_decent_discount or offer.has_coupon or offer.brand or offer.has_official_store):
        offer.reject_reason = "sem diferencial: sem desconto >=20%, cupom, marca ou loja oficial"
        return False

    # ── R3. Categoria "outros" com score < 70 → REJEITAR ────────────────
    # Produtos sem categoria definida dificilmente convertem
    if offer.category == "outros" and offer.score < 70:
        offer.reject_reason = f"categoria 'outros' com score insuficiente ({offer.score}/100, mínimo: 70)"
        return False

    # ── R4. Moda barata: moda + preço < R$80 → REJEITAR ─────────────────
    # Camisetas genéricas, chinelos baratos, etc.
    if offer.category == "moda" and offer.price_now is not None and offer.price_now < 80:
        offer.reject_reason = f"moda barata (R${offer.price_now:.2f}) abaixo do mínimo de R$80"
        return False

    # ── R4.5. Moda sem marca reconhecida → REJEITAR ──────────────────────
    # Bolsas, malas, óculos de marcas desconhecidas têm baixíssima conversão
    # Exceção: score >= 75 (produto viral com desconto brutal)
    if offer.category == "moda" and not offer.brand and offer.score < 75:
        offer.reject_reason = (
            f"moda sem marca reconhecida e score insuficiente "
            f"({offer.score}/100, mínimo para moda sem marca: 75)"
        )
        return False

    # ── R5. Saúde e beleza barata: preço < R$70 → REJEITAR ──────────────
    # Cremes genéricos, perfumes baratos, etc.
    if offer.category == "saude_beleza" and offer.price_now is not None and offer.price_now < 70:
        offer.reject_reason = f"saúde/beleza barata (R${offer.price_now:.2f}) abaixo do mínimo de R$70"
        return False

    # ── R5.5. Saúde/beleza sem marca reconhecida → REJEITAR ─────────────
    # Kits e produtos de marcas desconhecidas têm baixa credibilidade.
    # Exceção: desconto brutal (>= 60%) com score >= 72 compensa a ausência de marca
    if offer.category == "saude_beleza" and not offer.brand and offer.score < 72:
        offer.reject_reason = (
            f"saúde/beleza sem marca reconhecida e score insuficiente "
            f"({offer.score}/100, mínimo para saúde/beleza sem marca: 72)"
        )
        return False

    # ── R6. Produto genérico sem marca → REJEITAR (quando score baixo) ──
    # Produto claramente genérico E sem marca E score < 70
    if _is_generic_product(offer.raw_text) and not offer.brand and offer.score < 70:
        offer.reject_reason = f"produto genérico sem marca e score insuficiente ({offer.score}/100)"
        return False

    # ── R7. Score mínimo global ─────────────────────────────────────────
    if offer.score < cfg["min_score"]:
        offer.reject_reason = f"score insuficiente ({offer.score}/100, mínimo: {cfg['min_score']})"
        return False

    # ── R8. Limites diários ─────────────────────────────────────────────
    # Apenas ofertas com score >= 80 (min_score_bypass_limit) ignoram limites
    status = daily_status(cfg)
    bypass_limit = offer.score >= cfg.get("min_score_bypass_limit", 80)

    if not bypass_limit:
        # Limite diário global
        if status["postados_hoje"] >= cfg["max_posts_per_day"]:
            offer.reject_reason = f"limite diário atingido ({cfg['max_posts_per_day']}/dia)"
            return False

        # Limite por categoria
        category_count = status.get("por_categoria", {}).get(offer.category, 0)
        if category_count >= cfg["max_per_category_day"]:
            offer.reject_reason = (
                f"limite de categoria ({offer.category}: "
                f"{category_count}/{cfg['max_per_category_day']})"
            )
            return False

        # Anti-spam: após 2+ posts na mesma categoria, exigir score mais alto
        if category_count >= 2 and offer.score < 75:
            offer.reject_reason = (
                f"anti-spam: já foram {category_count} posts em '{offer.category}' "
                f"hoje e o score ({offer.score}) é insuficiente para nova publicação"
            )
            return False

        # ── R8.5. Anti-spam por janela de tempo ──────────────────────────
        # Garante cooldown mínimo entre posts consecutivos.
        # Evita rajadas de 3-4 produtos nos mesmos 5 minutos.
        interval = cfg.get("min_interval_minutes", 10)
        if interval > 0:
            posts_recent = _posts_in_last_minutes(cfg["db_path"], interval)
            if posts_recent > 0:
                offer.reject_reason = (
                    f"anti-spam: {posts_recent} post(s) nos últimos "
                    f"{interval}min — aguarde o cooldown"
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


def _posts_in_last_minutes(db_path: str, minutes: int) -> int:
    """Retorna quantos posts aprovados ocorreram nos últimos `minutes` minutos."""
    cutoff = (datetime.now(TZ_BR) - timedelta(minutes=minutes)).isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM offer_filter_events
            WHERE approved = 1 AND created_at >= ?
            """,
            (cutoff,),
        )
        return cursor.fetchone()[0]


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
