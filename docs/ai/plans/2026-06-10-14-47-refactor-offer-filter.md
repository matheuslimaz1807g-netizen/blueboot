# Plano: Refatoração do Offer Filter para Redução de Ofertas de Baixa Qualidade

## Situação Atual
- Sistema aprova mais de 100 ofertas/dia
- Ofertas genéricas (Gloss R$59, Perfume R$62, Creme R$49) passam pelo filtro
- Bypass de limite com score 55 é muito permissivo
- Score mínimo (38) muito baixo
- Sistema não filtra adequadamente moda barata, saúde e beleza barata

## Problemas Identificados

1. **DEFAULT_CONFIG muito permissivo**: min_score=38, min_score_bypass_limit=55
2. **Score desbalanceado**: bônus excessivos para categorias contínuas (+15), preços baixos (+20)
3. **Sem regras de rejeição específicas**: não há barreiras para "outros", moda barata, saúde barata
4. **Sem proteção contra produtos genéricos**: marca não é exigida como diferencial
5. **Bypass muito baixo**: score 55 permite que ofertas medianas ignorem limites diários

## Soluções Propostas

### 1. DEFAULT_CONFIG
- max_posts_per_day: 15 → 20 (limite total razoável)
- max_per_category_day: 3 → 4 (espaço para variedade sem excesso)
- min_score: 38 → 60 (somente ofertas boas passam)
- min_score_bypass_limit: 55 → 80 (somente ofertas excelentes ignoram limites)
- min_discount_pct: 30 → 25 (ajuste fino)

### 2. Rebalanceamento do Score
- Marca reconhecida: +20 (mantido - essencial)
- Loja oficial: +15 → +10 (reduzido pois é menos relevante que marca)
- Categorias: +15 → +10 (reduzido, ainda prioriza categorias fortes)
- Preço: reduzir bônus geral para evitar que produtos baratos passem fácil
- Desconto: AUMENTAR drasticamente o peso - ofertas com 70%+ viram destaque
- Benefícios: reduzir ligeiramente para balancear

### 3. Novas Regras de Rejeição
- "outros" + score < 70 → REJEITAR
- moda + preço < R$80 → REJEITAR
- saude_beleza + preço < R$70 → REJEITAR
- Sem diferencial → REJEITAR (desconto>=20%, cupom, marca, loja oficial)

### 4. Melhorias Inteligentes
- Anti-spam por categoria (após 2 publicações, exigir score maior)
- Valorização de marcas premium (iPhone, Dyson, etc.)
- Detecção de produtos genéricos (sem marca + categoria genérica = rejeição agressiva)
- Price drop detection bônus

## Riscos e Mitigação
- Risco: Bloquear ofertas legítimas de R$50-R$80 → Mitigação: ofertas com marca forte ainda passam
- Risco: Categoria "outros" morrer → Mitigação: é proposital, filtrar para evitar spam
- Risco: Queda no volume de publicações → Mitigação: qualidade sobre quantidade

## Critérios de Sucesso
- Redução de 100+/dia para 20-40/dia
- Zero ofertas genéricas sem marca passando
- Aumento da taxa de conversão das ofertas publicadas
- Marcas fortes e descontos reais como maioria das publicações
