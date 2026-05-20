# Plan: Otimização de Previsualização de Itens e Correção de ETA na Fila

## Problema
1. O texto exibido para cada item da fila é genérico (ex: "BOM, BONITO E BARATO ...") porque mostra a primeira linha (headline) do canal de origem, em vez de mostrar o nome real do produto (ex: "Kit 10 Pote De Vidro...").
2. O ETA estimado de envio para os itens na fila é exibido com o mesmo horário para o segundo item (ex: dois itens em `09:56:37`), pois a lógica de simulação de burst em `_refresh_queue_snapshot` está desalinhada com a lógica de execução real de burst no `_delivery_worker`.

## Soluções
1. **Extração Inteligente do Título**: Modificar a extração de preview em `_refresh_queue_snapshot()` para ignorar o headline (primeira linha não-vazia do canal original, exatamente como a pipeline de limpeza faz) e usar o título real do produto (segunda linha não-vazia). Também remover hashtags para garantir visual premium e limpo.
2. **Simulação de ETA Precisa**: Atualizar a lógica de cálculo do ETA em `_refresh_queue_snapshot()` para simular exatamente a lógica de burst e cooldown do `_delivery_worker`.

## Arquivos Alterados
- `executable/bot_runner.py`
