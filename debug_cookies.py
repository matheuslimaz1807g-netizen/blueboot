#!/usr/bin/env python3
"""
Debug script para verificar se ML_COOKIES está sendo lido corretamente
Execute na VPS: python3 debug_cookies.py
"""

import os
import sys

print("=" * 70)
print("🔍 DEBUG: Verificando ML_COOKIES")
print("=" * 70)

# Verificar variável bruta
ml_raw = os.getenv("ML_COOKIES", "")
print(f"\n1️⃣  ML_COOKIES RAW:")
print(f"   Tipo: {type(ml_raw)}")
print(f"   Tamanho: {len(ml_raw)} caracteres")
print(f"   Primeiros 100 chars: {ml_raw[:100]}")
print(f"   Últimos 100 chars: {ml_raw[-100:]}")

# Verificar se tem aspas problemáticas
if ml_raw.startswith('"') or ml_raw.startswith("'"):
    print(f"\n⚠️  AVISO: Cookie começa com aspas!")
    print(f"   Primeira char: {repr(ml_raw[0])}")
    print(f"   Última char: {repr(ml_raw[-1])}")

# Depois de strip()
ml_stripped = ml_raw.strip()
print(f"\n2️⃣  ML_COOKIES após .strip():")
print(f"   Tamanho: {len(ml_stripped)} caracteres")
print(f"   Primeiros 100 chars: {ml_stripped[:100]}")

# Dividir por ;
cookies_list = ml_stripped.split(';')
print(f"\n3️⃣  Cookies divididos por ';':")
print(f"   Total de chunks: {len(cookies_list)}")
for i, cookie in enumerate(cookies_list[:5]):  # Mostrar primeiros 5
    print(f"   [{i}] {cookie[:80]}")

# Verificar parsing de cada cookie
print(f"\n4️⃣  Parsing de cada cookie:")
valid_count = 0
for i, cookie_chunk in enumerate(cookies_list):
    cookie_chunk = cookie_chunk.strip()
    if not cookie_chunk or '=' not in cookie_chunk:
        print(f"   [{i}] ❌ Inválido (sem '=')")
        continue
    
    try:
        name, value = cookie_chunk.split('=', 1)
        name = name.strip()
        value = value.strip()
        print(f"   [{i}] ✓ {name}={value[:30]}...")
        valid_count += 1
    except Exception as e:
        print(f"   [{i}] ❌ Erro: {e}")

print(f"\n5️⃣  Resumo:")
print(f"   Cookies válidos: {valid_count}/{len(cookies_list)}")

if valid_count == 0:
    print("\n❌ PROBLEMA: Nenhum cookie válido encontrado!")
    print("   Verifique no .env:")
    print("   - ML_COOKIES não deve ter aspas duplas/simples")
    print("   - Formato correto: ML_COOKIES=cookie1=val1;cookie2=val2")
else:
    print(f"\n✅ OK: {valid_count} cookies prontos para injetar")

print("\n" + "=" * 70)
