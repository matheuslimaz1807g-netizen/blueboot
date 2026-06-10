# Mudanças: Refatoração do Offer Filter

## Data
2026-06-10 14:47

## Arquivo Modificado
- `executable/offer_filter.py` — Refatoração completa do sistema de pontuação e filtragem
- `api/tests/test_offer_filter.py` — Atualização dos testes para o novo sistema

## O que mudou

### 1. DEFAULT_CONFIG
| Parâmetro | Antes | Depois | Motivo |
|-----------|-------|--------|--------|
| max_posts_per_day | 15 | 20 | Aumento moderado (20 posts/dia é razoável) |
| max_per_category_day | 3 | 4 | Pequeno ajuste para variedade |
| min_score | 38 | 60 | Aumento DRÁSTICO - só passa oferta boa mesmo |
| min_discount_pct | 30 | 25 | Ajuste fino |
| min_score_bypass_limit | 55 | 80 | **Principal mudança** - só ofertas excelentes ignoram limites |

### 2. BYPASS DE LIMITE (Antes vs Depois)
- **Antes**: score >= 55 ignorava limites diários → gerava +100 posts/dia
- **Depois**: score >= 80 ignora limites → apenas ofertas realmente excepcionais

### 3. Sistema de Score Rebalanceado

| Componente | Antes | Depois |
|-----------|-------|--------|
| Marca reconhecida | +20 | +20 (mantido) |
| Loja oficial | +15 | +10 (reduzido) |
| Categoria prioritária | +15 | +10 (reduzido) |
| Preço R$15-200 | +20 | +10 (reduzido DRÁSTICAMENTE) |
| Preço R$200-500 | +12 | +8 |
| Preço R$500-1500 | +6 | +5 |
| Preço > R$1500 | +10 | +8 |
| Desconto 70%+ | +20 | +30 (AUMENTADO) |
| Desconto 60%+ | +15 | +25 (AUMENTADO) |
| Desconto 50%+ | +12 | +20 (AUMENTADO) |
| Desconto 40%+ | +8 | +15 |
| Desconto 30%+ | +4 | +10 |
| Desconto 20%+ | +1 | +5 |
| Benefícios (3+) | +15 | +10 |
| Benefícios (2) | +8 | +5 |
| Benefícios (1) | +4 | +2 |
| Horário pico | +5 | +3 |
| **Bônus Premium** | — | **+5** (NOVO) |
| **Penalidade Genérico** | — | **-10** (NOVO) |
| **Bônus Price Drop** | — | **+5** (NOVO) |

### 4. Novas Regras de Rejeição

1. **Sem diferencial**: Toda oferta precisa de pelo menos UM: desconto >= 20%, cupom, marca ou loja oficial
2. **Categoria "outros"**: Score < 70 → REJEITAR (mesmo se passar no score mínimo)
3. **Moda barata**: moda + preço < R$80 → REJEITAR (camisetas genéricas, chinelos)
4. **Saúde/beleza barata**: saude_beleza + preço < R$70 → REJEITAR (cremes, perfumes genéricos)
5. **Produto genérico**: genérico + sem marca + score < 70 → REJEITAR
6. **Anti-spam por categoria**: após 2+ posts na mesma categoria, exigir score >= 75

### 5. Melhorias Inteligentes

- **Anti-spam por categoria**: Após 2 publicações na mesma categoria, o sistema exige score >= 75 para aprovar mais. Isso evita que uma única categoria domine o feed.
- **Detecção de produtos genéricos**: Palavras como "genérico", "similar", "paralelo", "sem marca" ativam penalidade de -10 no score.
- **Bônus premium**: Produtos de alto valor (iPhone, Dyson, Playstation, etc.) recebem +5.
- **Bônus price drop**: Queda de preço registrada no dia gera +5.
- **TRUSTED_BRANDS expandido**: Marcas como Apple, LG, Sony, Dyson, Stanley, Dewalt, Vans, New Balance, Lenovo, Dell e várias outras foram adicionadas.
- **Marcas premium**: Dyson, Bose, Marshall, Nintendo, etc. são reconhecidas e valorizadas.

## Impacto Esperado

### Quantidade de Ofertas Aprovadas por Dia
- **Antes**: 100+ ofertas/dia
- **Depois**: 20-40 ofertas/dia (redução de 60-80%)
- O limite diário de 20 é o teto, mas na prática muitas ofertas serão rejeitadas por:
  - Score insuficiente
  - Categoria "outros" barrada
  - Moda/saúde barata
  - Sem diferencial

### Qualidade das Ofertas
- **Antes**: Gloss R$59, Perfume R$62, Creme R$49, camisetas genéricas
- **Depois**: Marcas reconhecidas com descontos reais, eletrônicos com cupom, produtos com diferencial claro
- O score mínimo de 60 e as regras de rejeição eliminam ofertas fracas

### Efeito do Bypass de Score 80
- **Antes**: Score 55 = bypass. Qualquer oferta com marca e 10% de desconto passava.
- **Depois**: Score 80 = bypass. Precisa de marca + desconto forte + múltiplos benefícios OU premium.
  - Exemplo que atinge 80: Samsung Galaxy S23 com 70% off + frete + cupom + pix (20+10+5+30+10+5 = 80)
  - Muito mais seletivo, apenas ofertas realmente bombásticas ignoram limites

## Testes
- 11 testes passando (100%)
- Os testes existentes foram adaptados para o novo sistema de pontuação
- Novos testes adicionados:
  - `test_should_post_rejects_moda_barata`
  - `test_should_post_rejects_saude_beleza_barata`
  - `test_should_post_rejects_outros_with_low_score`
  - `test_should_post_rejects_generic_product`
