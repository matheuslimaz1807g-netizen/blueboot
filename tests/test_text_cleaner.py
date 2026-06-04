"""
test_text_cleaner.py — Testes unitários para o módulo de curadoria local.
"""
from __future__ import annotations

import os
import sys

# Garante que o diretório executable está no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "executable"))

from text_cleaner import clean_offer_text


def test_lobas_replacement():
    raw = "PRAS LOBAS CHIQUES E CHEIROSAS \n🧴LACOSTE POUR FEMME EDP 30 ML\n💵Por R$192,90 em até 6x R$ 32,15 sem juros"
    cleaned = clean_offer_text(raw)
    # The headline is forced to UPPERCASE and 'LOBAS' becomes 'MULHERES'
    assert "PRAS MULHERES CHIQUES E CHEIROSAS" in cleaned
    assert "LOBAS" not in cleaned
    assert "LACOSTE POUR FEMME" in cleaned
    assert "R$192,90" in cleaned

def test_lobo_case_preserving():
    raw = "AQUELE KIT LOBO CHEIROSO\n🧴 Kit Body Splash Masculino\n💵 Por: R$89 no pix"
    cleaned = clean_offer_text(raw)
    assert "AQUELE KIT HOMEM CHEIROSO" in cleaned
    assert "LOBO" not in cleaned

def test_loba_case_preserving():
    raw = "É DESSE QUE A LOBA GOSTA \n🧴Gabriela Sabatini 60Ml\n💵De R$169,00"
    cleaned = clean_offer_text(raw)
    assert "É DESSE QUE A MULHER GOSTA" in cleaned

def test_tropa_replacement():
    raw = "Aí pra tropa que pediu!\n📱 Xiaomi Redmi Note 13\nR$ 1200,00"
    cleaned = clean_offer_text(raw)
    assert "tropa" not in cleaned.lower()
    assert "galera" in cleaned.lower()
    assert "Xiaomi" in cleaned

def test_junk_lines_removal():
    raw = "Fala galera do grupo!\n\n💻 Notebook Gamer\nDe R$ 5000 por R$ 4000\n\nCorre que acaba!\nValeu pessoal"
    cleaned = clean_offer_text(raw)
    assert "Fala galera" not in cleaned
    assert "Corre que acaba" not in cleaned
    assert "Valeu pessoal" not in cleaned
    assert "Notebook Gamer" in cleaned
    assert "R$ 4000" in cleaned

def test_hashtag_removal():
    raw = "Oferta boa!\n📱 iPhone 13\nR$ 3500\n#ofertas #apple #lobaodasofertas"
    cleaned = clean_offer_text(raw)
    assert "#ofertas" not in cleaned
    assert "iPhone 13" in cleaned

def test_protection_rules():
    raw = "Bom dia!\nCUPOM10OFF\nFrete Grátis\nLoja Oficial\nPix e Boleto\nhttps://mercadolivre.com"
    cleaned = clean_offer_text(raw)
    assert "Bom dia" not in cleaned
    assert "CUPOM10OFF" in cleaned
    assert "Frete Grátis" in cleaned
    assert "Loja Oficial" in cleaned
    assert "Pix e Boleto" in cleaned
    assert "https://mercadolivre.com" in cleaned

def test_coherent_opening():
    raw = "E com esse desconto!\n🔋 Power Bank 20000mAh\nR$ 100"
    cleaned = clean_offer_text(raw)
    # _ensure_coherent_opening prepends the product title if the text starts with a dangling connector
    assert cleaned.startswith("🔋 Power Bank 20000mAh")
    assert "R$ 100" in cleaned

def test_group_slogans_removal():
    raw = "Aqui no nosso canal você acha tudo\nRelógio Casio\nR$ 150"
    cleaned = clean_offer_text(raw)
    assert "nosso canal" not in cleaned.lower()
    assert "Relógio Casio" in cleaned

def test_multiple_emojis_only_line():
    raw = "🔥🔥🚨🚨🚨\nNotebook\nR$ 2000\n🔥🔥🔥"
    cleaned = clean_offer_text(raw)
    assert "🔥🔥🚨🚨🚨" not in cleaned
    assert "🔥🔥🔥" not in cleaned
    assert "NOTEBOOK" in cleaned
