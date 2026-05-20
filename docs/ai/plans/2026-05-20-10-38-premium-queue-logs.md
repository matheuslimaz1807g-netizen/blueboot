# Plan: Exibição Premium de Produtos na Fila de Envio (Título, Preço e Loja)

## Problema
O log de visualização da fila ainda pode ser enriquecido. Em alguns casos, ele mostra a linha de cupom/desconto (ex: "💵 R$10 OFF em R$79") em vez de capturar o título do produto real. Além disso, seria muito mais profissional e útil mostrar mais informações sobre a oferta na fila.

## Solução
1. **Filtro Inteligente de Título**: Implementar uma heurística robusta que ignora linhas com cupons, descontos, palavras de ação (compre, link, clique, etc.) para extrair com 100% de precisão o título do produto físico real.
2. **Layout Premium (Enriquecimento com Preço e Loja)**: Detectar o preço da promoção (`R$ XX,XX`) e o nome da loja de origem (Mercado Livre, AliExpress, Shopee) e exibi-los ao lado do título usando um separador elegante `|`.
   - Exemplo: `📚 Kindle 11ª Geração 16GB | R$ 499 | Mercado Livre`

## Arquivos Alterados
- `executable/bot_runner.py`
