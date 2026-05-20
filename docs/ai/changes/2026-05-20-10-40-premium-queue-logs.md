# Log de Mudanças - Previsualização Premium com Filtro de Cupons e Info da Oferta na Fila

**Data**: 2026-05-20 10:40 (BRT)

## Mudanças Realizadas
1. **Filtro Inteligente de Títulos na Fila (`_refresh_queue_snapshot` em `bot_runner.py`)**:
   - Desenvolvida uma heurística de extração que analisa cada linha da mensagem e ignora automaticamente linhas com links, hashtags ou termos comerciais e de cupom (ex: "compre", "cupom", "off", "desconto", "valor").
   - Isso garante que, se uma promoção tiver um headline de cupom como primeira/segunda linha (ex: `💵 R$10 OFF em R$79`), o parser pule essas linhas comerciais e extraia o **nome físico real do produto** (ex: `📚 Kindle 11ª Geração 16GB`).

2. **Enriquecimento com Preço e Loja**:
   - O parser agora detecta o preço em reais (`R$ XXX,XX`) diretamente do corpo da mensagem.
   - Detecta a loja correspondente analisando links do Mercado Livre, Shopee ou AliExpress.
   - Formata a saída no snapshot de forma ultra premium usando um separador elegante `|`:
     * Exemplo: `📚 Kindle 11ª Geração 16GB | R$ 79 | Mercado Livre`
     * Exemplo: `🚿 Lorenzetti Loren Shower Ultra... | R$ 139 | Mercado Livre`

## Arquivos Alterados
- `executable/bot_runner.py`

## Resultados Esperados
- O painel do cliente agora exibe a fila de envio de forma extremamente clara, rica em contexto e limpa de termos de cupom redundantes.
