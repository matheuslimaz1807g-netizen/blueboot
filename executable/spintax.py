"""
spintax.py - Motor de Copywriting Dinâmico para humanização de ofertas.
"""
import random
from typing import Optional

# ── Dicionários de Spintax ───────────────────────────────────────────────────

# 1. Nível Bug (Score > 80): Urgência máxima, caixa alta, emojis de sirene.
BUG_OPENERS = [
    "🚨 GENTE DO CÉU OLHA ISSO!",
    "🚨 BUG DE PREÇO ABSURDO!",
    "🚨 CORRE QUE VAI ACABAR RÁPIDO!",
    "🚨 ATENÇÃO! PREÇO TOTALMENTE FORA DO NORMAL!",
    "🚨 MEU DEUS, TÁ DE GRAÇA!",
]

BUG_MIDDLES = [
    "Achei essa pérola agora e já garanti o meu.",
    "Nunca vi tão barato, sério.",
    "Se você precisava, a hora é agora.",
    "Isso aqui não dura 10 minutos no estoque.",
    "Menor preço histórico disparado.",
]

# 2. Nível Ótima Oportunidade (Score 60 - 79): Recomendação forte.
GOOD_OPENERS = [
    "🔥 Ótima oportunidade na área, galera.",
    "🔥 Pra quem tava esperando baixar, olha aí.",
    "🔥 Preço despencou legal agora.",
    "🔥 Achei esse desconto muito bom, vale a pena.",
    "🔥 Dica boa do dia pra vocês.",
]

GOOD_MIDDLES = [
    "Tá valendo super a pena pelo preço.",
    "Excelente custo benefício hoje.",
    "Com esse desconto compensa demais.",
    "Estava monitorando e finalmente caiu.",
]

# 3. Nível Rotina (Score < 60): Informativo, reposição, desconto leve.
ROUTINE_OPENERS = [
    "📌 Reposição de estoque com um precinho bacana.",
    "📌 Oferta legal rolando agora.",
    "📌 Dica pra quem tava procurando:",
    "📌 Mais uma promoção ativada.",
    "📌 Preço bacana na loja agora.",
]

ROUTINE_MIDDLES = [
    "Um descontinho pra ajudar.",
    "Preço ok, bom pra quem tava precisando de um.",
    "Garante um troco de economia.",
    "Não é o menor do ano, mas tá num preço justo.",
]

# Fechamentos (CTAs) comuns para todos
CLOSERS = [
    "👇 Confere o link:",
    "👇 Pega o seu aqui:",
    "🔗 Link promocional:",
    "🛒 Acessa a oferta aqui:",
    "👇 Garante logo:",
]

def generate_humanized_copy(score: int, original_text: str, converted_link: str) -> str:
    """
    Gera um texto humanizado baseado no score da oferta.
    Substitui a cópia original robótica por um formato de recomendação.
    """
    if score >= 80:
        opener = random.choice(BUG_OPENERS)
        middle = random.choice(BUG_MIDDLES)
    elif score >= 60:
        opener = random.choice(GOOD_OPENERS)
        middle = random.choice(GOOD_MIDDLES)
    else:
        opener = random.choice(ROUTINE_OPENERS)
        middle = random.choice(ROUTINE_MIDDLES)
        
    closer = random.choice(CLOSERS)
    
    # Tentamos extrair o título ou nome do produto para manter o contexto
    # O raw text tem muita poluição. Vamos pegar as primeiras 2 linhas que não sejam o link.
    lines = [ln.strip() for ln in original_text.splitlines() if ln.strip()]
    product_lines = []
    
    # Filtro básico para limpar a mensagem original e pegar apenas a essência do produto
    avoid_terms = ["compre", "link", "aqui", "grupo", "oferta", "desconto", "http", "r$"]
    for line in lines:
        ll = line.lower()
        if "http" in ll or line.startswith("#"):
            continue
        if any(t in ll for t in avoid_terms):
            continue
        product_lines.append(line)
        
    # Extrair os preços se existirem no texto original
    import re
    price_matches = re.findall(r"(R\$\s*[\d.,]+)", original_text, re.IGNORECASE)
    price_info = ""
    if price_matches:
        prices = sorted(set(price_matches))
        if len(prices) >= 2:
            price_info = f"💰 De {prices[-1]} por {prices[0]}"
        else:
            price_info = f"💰 {prices[0]}"
            
    # Monta o contexto limpo
    product_context = "\n".join(product_lines[:2]) if product_lines else ""
    
    # Constrói a mensagem final
    parts = [
        opener,
        "",
        product_context,
        price_info if price_info else "",
        "",
        middle,
        closer,
        converted_link
    ]
    
    return "\n".join(p for p in parts if p) # Remove linhas vazias duplas se price_info estiver vazio
