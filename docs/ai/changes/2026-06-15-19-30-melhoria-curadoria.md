# Melhoria de Curadoria — 2026-06-15

## Problema Relatado
- Tag "PREÇO EXCELENTE" aparecendo em praticamente todas as mensagens
- Spam de ~3 produtos a cada 5 minutos
- Produtos de baixa qualidade sendo aprovados (Óculos Cacife R$52, Kit Body Splash sem marca)

## Causa Raiz Descoberta

### 1. min_score=40 no config_loader.py (BUG CRÍTICO)
`config_loader.py` usava `min_score=40` como padrão, enquanto o `offer_filter.py` usa `min_score=60`. Isso anulava toda a lógica de filtragem — produtos com score 40-59 passavam indevidamente.

### 2. Categorias incompletas
"Bolsa", "Mala", "Óculos", "Body Splash" caíam em `outros` e não eram filtrados pelas regras de categoria.

### 3. Sem cooldown por janela de tempo
O filtro controlava volume diário mas não impedia rajadas (3 produtos em 5 min).

### 4. Tag "PREÇO EXCELENTE" muito permissiva
Aplicada a score >= 50 (30% de chance), aparecia em ~30% de todas as mensagens aprovadas.

## Mudanças Realizadas

### config_loader.py
- `min_score`: 40 → **60** (alinhado com offer_filter.py)
- Adicionado `min_interval_minutes: 10` (configurável via `OFFER_FILTER_MIN_INTERVAL_MINUTES`)

### offer_filter.py

#### DEFAULT_CONFIG
- Adicionado `min_interval_minutes: 10`

#### CATEGORIES — Palavras-chave expandidas
- **moda**: adicionado bolsa, mala, mochila, carteira, óculos, boné, gorro, bermuda, legging, top, etc.
- **saude_beleza**: adicionado body splash, hidratante, sabonete, gel, desodorante, kit perfume, maquiagem, sérum, etc.
- **eletronicos**: adicionado smartphone, galaxy, redmi, poco, motorola, moto g

#### Novas Regras de Filtragem
- **R4.5**: Moda sem marca reconhecida + score < 75 → REJEITAR
- **R5.5**: Saúde/beleza sem marca + score < 72 → REJEITAR
- **R8.5**: Cooldown — se houve post aprovado nos últimos `min_interval_minutes` → REJEITAR

#### Nova Função
- `_posts_in_last_minutes(db_path, minutes)` — consulta SQLite para cooldown

### pipeline.py
- Removido bloco `elif offer.score >= 50: urgency_tag = "⚡ PREÇO EXCELENTE"`
- `urgency_tag` agora só aparece em `is_price_drop` ou `score >= 70`

## Impacto Esperado (com as ofertas do exemplo)

| Produto | Antes | Depois |
|---------|-------|--------|
| Bolsa Adidas R$211 | Aprovada (score 35, min=40) | **Rejeitada** (score 56 < 60) |
| Mala Adidas R$193 | Aprovada | **Aprovada** ✓ (marca + desconto 35%) |
| Kit Body Splash s/ marca | Aprovada | **Rejeitada** (R5.5: saúde/beleza sem marca) |
| Óculos Cacife R$52 | Aprovada | **Rejeitada** (R4: moda barata < R$80) |
| Samsung Galaxy S25 | Aprovada | **Aprovada** ✓ (samsung, eletronicos) |

## Testes
- 11/11 testes existentes continuam passando
- Nenhum teste quebrado

## Próximos Passos Recomendados
1. Adicionar testes para as regras R4.5, R5.5 e R8.5 (cooldown)
2. Monitorar os logs do bot nas próximas 24h para calibrar o `min_interval_minutes`
3. Avaliar se a Mala Adidas (score 66) tem uma conversão boa o suficiente para justificar aprovação
