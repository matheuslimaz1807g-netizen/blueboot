"""
text_cleaner.py — Motor de curadoria local inteligente para textos de ofertas.

Estratégia em 3 camadas:
  1. Substituição inteligente — troca termos de grupo por equivalentes neutros
  2. Remoção seletiva — remove frases puramente genéricas sem valor
  3. Coerência — garante que o texto final faz sentido como post independente

Não usa LLM. Baseado em dicionários de padrões e regex.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


# ── Camada 1: Substituições inteligentes ──────────────────────────────────────
# Mapeia termos de grupo/mascote para equivalentes neutros.
# Ordem importa: padrões mais específicos primeiro.

_SUBSTITUTIONS: list[tuple[re.Pattern, str]] = [
    # ── Mascotes e apelidos de grupo ──────────────────────────────────────
    # "lobas/lobões/loba/lobão" → equivalente neutro por contexto
    (re.compile(r"\b(pras?\s+)lobas\b", re.IGNORECASE), r"\1mulheres"),
    (re.compile(r"\b(pros?\s+)lob[oõ]es\b", re.IGNORECASE), r"\1homens"),
    (re.compile(r"\b(al[oô]\s+)lobas\b", re.IGNORECASE), r"\1mulheres"),
    (re.compile(r"\b(al[oô]\s+)lob[oõ]es\b", re.IGNORECASE), r"\1homens"),
    (re.compile(r"\b(ei\s+)lobas\b", re.IGNORECASE), r"\1mulheres"),
    (re.compile(r"\b(ei\s+)lob[oõ]es\b", re.IGNORECASE), r"\1homens"),
    (re.compile(r"\b(o\s+)lobo\b", re.IGNORECASE), r"\1homem"),
    (re.compile(r"\b(a\s+)loba\b", re.IGNORECASE), r"\1mulher"),
    (re.compile(r"\b(ao\s+)lobo\b", re.IGNORECASE), r"\1homem"),
    (re.compile(r"\b(d[oa]\s+)lob[oa]\b", re.IGNORECASE), r"\1homem"),
    (re.compile(r"\blobas\b", re.IGNORECASE), "mulheres"),
    (re.compile(r"\blob[oõ]es\b", re.IGNORECASE), "homens"),
    (re.compile(r"\bloba\b", re.IGNORECASE), "mulher"),
    (re.compile(r"\blobo\b", re.IGNORECASE), "homem"),
    (re.compile(r"\blob[aã]o\b", re.IGNORECASE), "pessoal"),
    (re.compile(r"\bmatilha\b", re.IGNORECASE), "galera"),

    # ── Outros mascotes comuns de grupos BR ───────────────────────────────
    (re.compile(r"\b(pras?\s+)tropa\b", re.IGNORECASE), r"\1galera"),
    (re.compile(r"\b(pros?\s+)tropa\b", re.IGNORECASE), r"\1galera"),
    (re.compile(r"\b(da\s+)tropa\b", re.IGNORECASE), r"\1galera"),
    (re.compile(r"\b(pras?\s+)feras\b", re.IGNORECASE), r"\1pessoal"),
    (re.compile(r"\b(pros?\s+)feras\b", re.IGNORECASE), r"\1pessoal"),
    (re.compile(r"\b(pras?\s+)cubs\b", re.IGNORECASE), r"\1pessoal"),
    (re.compile(r"\b(pros?\s+)cubs\b", re.IGNORECASE), r"\1pessoal"),
    (re.compile(r"\b(pras?\s+)minas\b", re.IGNORECASE), r"\1mulheres"),
    (re.compile(r"\b(pros?\s+)manos\b", re.IGNORECASE), r"\1homens"),
    (re.compile(r"\b(al[oô]\s+)tropa\b", re.IGNORECASE), r"\1galera"),
    (re.compile(r"\b(al[oô]\s+)feras\b", re.IGNORECASE), r"\1pessoal"),
    (re.compile(r"\btropa\b(?!\s+de)", re.IGNORECASE), "galera"),

    # ── Referências ao canal/grupo genéricas ──────────────────────────────
    (re.compile(r"\b(d[oa]\s+)(nosso\s+)?(grupo|canal)\b", re.IGNORECASE), ""),
    (re.compile(r"\baqui\s+no\s+(grupo|canal)\b", re.IGNORECASE), ""),
    (re.compile(r"\bno\s+nosso\s+(grupo|canal)\b", re.IGNORECASE), ""),
    (re.compile(r"\bnesse\s+(grupo|canal)\b", re.IGNORECASE), ""),
    (re.compile(r"\bgalera\s+do\s+(grupo|canal)\b", re.IGNORECASE), "galera"),
    (re.compile(r"\bpessoal\s+do\s+(grupo|canal)\b", re.IGNORECASE), "pessoal"),
]

# ── Camada 2: Linhas a remover completamente ─────────────────────────────────
# Frases puramente genéricas que não carregam informação do produto.
# Só remove se a linha INTEIRA for isso (não remove linhas que também têm dados).

_JUNK_LINE_PATTERNS: list[re.Pattern] = [
    # Frases motivacionais genéricas
    re.compile(r"^\s*(?:n[aã]o\s+perca|corre\s+que\s+acaba|aproveita?\s*!*|vai\s+acabar|[uú]ltima\s+chance|corre(?:r?e?)?\s*!+)\s*[!🔥🚨]*\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:bora|vamos|partiu)\s*!*\s*[🔥🚨💥]*\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:ofert(?:a[çc][oã]|ona)|que\s+pre[çc]o|imperd[ií]vel)\s*!*\s*[🔥🚨]*\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:corre(?:e+)?|corram)\s*!*\s*[🔥🚨]*\s*$", re.IGNORECASE),

    # Cumprimentos e despedidas soltos
    re.compile(r"^\s*(?:bom\s+dia|boa\s+(?:tarde|noite)|fala\s+(?:galera|pessoal)|e\s+a[ií]\s+(?:galera|pessoal))\s*[!,]*\s*[👋🌞🌙]*\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:at[eé]\s+mais|valeu(?:\s+(?:pessoal|galera))?|tmj|abra[çc]os?)\s*[!]*\s*[👋]*\s*$", re.IGNORECASE),

    # Chamadas de atenção desconectadas do produto
    re.compile(r"^\s*(?:e\s+esses?\s+dentes?\s+manchad[oa]s?\s+a[ií]\s*\??|coloque?\s+senha\s+no\s+seu\s+cafof[oó])\s*[!?]*\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:al[oô]\s+(?:mulherada|rapaziada|galerinha|moçada))\s*[!]*\s*[🔥💃]*\s*$", re.IGNORECASE),

    # Referências a membros/compartilhamento
    re.compile(r"^\s*(?:siga\s+nosso|entre\s+no\s+(?:grupo|canal)|compartilh[ae]|indica\s+(?:pr[oa]|pra)\s+(?:um|uma)\s+amig[oa])\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*@\w+\s*$"),

    # Hashtags de grupo (sem conteúdo de produto)
    re.compile(r"^\s*(?:#\w+\s*)+$"),

    # Linhas que são só emojis
    re.compile(r"^\s*[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U0000FE00-\U0000FE0F\U0000200D\s]+\s*$"),
]

# ── Camada 2b: Padrões de proteção (nunca remover linhas com estes) ───────────

_PROTECTED_PATTERNS: list[re.Pattern] = [
    re.compile(r"R\$", re.IGNORECASE),                          # Preço
    re.compile(r"https?://", re.IGNORECASE),                     # Link
    re.compile(r"\b(?:cupom|c[oó]digo|coupon)\b", re.IGNORECASE),# Cupom
    re.compile(r"\b\d+x\s*(?:de\s*)?R\$", re.IGNORECASE),       # Parcelamento
    re.compile(r"\b(?:pix|boleto)\b", re.IGNORECASE),            # Pagamento
    re.compile(r"\bfrete\s*gr[aá]tis\b", re.IGNORECASE),        # Frete
    re.compile(r"\bloja\s*oficial\b", re.IGNORECASE),            # Loja oficial
    re.compile(r"\b\d+\s*(?:mAh|ml|ML|GB|TB|kg|g|W|V|pol|\")\b"),# Especificações
    re.compile(r"\brecorr[eê]ncia\b", re.IGNORECASE),           # Recorrência
]


# ── Camada 3: Detecção de abertura incoerente ─────────────────────────────────

_DANGLING_START = re.compile(
    r"^\s*(?:e\s+|por\s+apenas|com\s+(?:desconto|cupom)|mas\s+|porém\s+|além\s+|também\s+)",
    re.IGNORECASE,
)

_PRODUCT_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF]"  # Misc symbols & pictographs
)


# ── API pública ───────────────────────────────────────────────────────────────

def clean_offer_text(text: str) -> str:
    """
    Curadoria local inteligente de texto de oferta.

    1. Aplica substituições inteligentes (mascotes → termos neutros)
    2. Remove linhas puramente genéricas (sem dados de produto)
    3. Garante coerência da abertura

    Args:
        text: Texto bruto copiado de grupo do Telegram.

    Returns:
        Texto limpo e coerente, pronto para postar.
    """
    if not text or not text.strip():
        return text

    # ── Passo 1: Substituições inteligentes (mantendo a caixa) ────────────
    cleaned = text
    for pattern, replacement in _SUBSTITUTIONS:
        cleaned = _case_preserving_sub(pattern, replacement, cleaned)

    # ── Passo 2: Remoção de linhas lixo ───────────────────────────────────
    lines = cleaned.splitlines()
    kept_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Linha vazia → preservar (será colapsada depois)
        if not stripped:
            kept_lines.append("")
            continue

        # Linha protegida → nunca remover
        if _is_protected(stripped):
            kept_lines.append(line)
            continue

        # Linha lixo → remover
        if _is_junk_line(stripped):
            continue

        # Linha normal → manter
        kept_lines.append(line)

    # ── Passo 3: Limpeza de formatação ────────────────────────────────────
    result = _collapse_blanks(kept_lines)

    # ── Passo 4: Coerência de abertura ────────────────────────────────────
    result = _ensure_coherent_opening(result, text)

    # ── Passo 4.5: Primeira parte em Caps Lock ────────────────────────────
    result = _force_headline_caps(result)

    # ── Passo 5: Limpar espaços duplos gerados por substituições ──────────
    result = _clean_extra_spaces(result)

    return result.strip()


# ── Funções internas ──────────────────────────────────────────────────────────

def _is_protected(line: str) -> bool:
    """Verifica se a linha contém dados do produto que não devem ser removidos."""
    return any(p.search(line) for p in _PROTECTED_PATTERNS)


def _is_junk_line(line: str) -> bool:
    """Verifica se a linha é puramente genérica/lixo."""
    return any(p.match(line) for p in _JUNK_LINE_PATTERNS)


def _collapse_blanks(lines: list[str]) -> str:
    """Colapsa múltiplas linhas em branco consecutivas em uma só."""
    result: list[str] = []
    blank_count = 0

    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 1:
                result.append("")
        else:
            blank_count = 0
            result.append(line)

    return "\n".join(result)


def _ensure_coherent_opening(text: str, original: str) -> str:
    """
    Se a primeira linha do texto limpo começa com conectivo solto ou
    parece truncada, cria uma abertura baseada no nome do produto.
    """
    lines = text.strip().splitlines()
    if not lines:
        return text

    first_line = lines[0].strip()

    # Se a primeira linha já parece um título de produto, está ok
    if not _DANGLING_START.match(first_line):
        return text

    # Tenta extrair o nome do produto do texto original
    product_title = _extract_product_title(original)
    if product_title:
        lines.insert(0, product_title)
        lines.insert(1, "")
        return "\n".join(lines)

    return text


def _extract_product_title(text: str) -> Optional[str]:
    """
    Tenta extrair o nome/título do produto do texto original.
    Procura linhas com especificações técnicas ou emojis de produto.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Linhas com especificações numéricas são provavelmente nomes de produto
        if re.search(r"\b\d+\s*(?:mAh|ml|ML|GB|TB|kg|g|W|V|pol|\")\b", stripped):
            return stripped

        # Linhas que começam com emoji de produto seguido de texto
        if _PRODUCT_EMOJI_RE.match(stripped) and len(stripped) > 5:
            # Não é uma linha só de emojis
            text_part = _PRODUCT_EMOJI_RE.sub("", stripped).strip()
            if len(text_part) > 3:
                return stripped

    return None


def _clean_extra_spaces(text: str) -> str:
    """Remove espaços duplos que podem surgir de substituições."""
    # Colapsa múltiplos espaços em um, linha por linha
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        cleaned_line = re.sub(r"  +", " ", line).strip()
        cleaned.append(cleaned_line)
    return "\n".join(cleaned)


def _case_preserving_sub(pattern: re.Pattern, replacement: str, text: str) -> str:
    """Substitui o padrão mantendo a caixa (maiúsculas/minúsculas) da string original."""
    def replacer(match: re.Match) -> str:
        # Expande \1, \2 etc na string de substituição
        res = match.expand(replacement)
        orig = match.group(0)
        
        # Copia a formatação de caixa
        if orig.isupper():
            return res.upper()
        elif orig.istitle() and len(orig) > 1:
            return res.title()
        elif orig.islower():
            return res.lower()
        
        # Se for misto, aplica caixa alta na primeira letra se a original for
        if orig and orig[0].isupper():
            return res[0].upper() + res[1:] if res else res
        return res

    return pattern.sub(replacer, text)


def _force_headline_caps(text: str) -> str:
    """Força a primeira linha (headline/abertura) a ficar em CAPS LOCK se não for o produto."""
    lines = text.splitlines()
    if not lines:
        return text

    # Verifica se a primeira linha é o nome do produto (contém emoji de produto ou especificação)
    # Se for o produto, não forçamos caps lock. A "primeira parte" que o usuário se refere
    # é a abertura genérica (ex: "É DESSE QUE A LOBA GOSTA")
    first_line = lines[0].strip()
    
    # Se a primeira linha não é o produto, transformamos em CAPS LOCK
    if first_line and not _PRODUCT_EMOJI_RE.match(first_line) and not re.search(r"\b\d+\s*(?:mAh|ml|ML|GB|TB|kg|g|W|V|pol|\")\b", first_line):
        lines[0] = first_line.upper()
        
    return "\n".join(lines)
