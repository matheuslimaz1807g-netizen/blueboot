# Log de Mudanças - Otimização de Preview e Alinhamento de ETA da Fila

**Data**: 2026-05-20 09:56 (BRT)

## Mudanças Realizadas
1. **Extração Inteligente do Título (`_refresh_queue_snapshot`)**:
   - O preview agora pula a primeira linha não-vazia (o headline genérico, ex: "BOM, BONITO E BARATO", "É HOJE QUE VOCÊ TROCA CELULAR...") e pega a segunda linha não-vazia, que contém o nome real do produto promocional (ex: "Kit 10 Pote De Vidro Marmita Hermética 640ml").
   - Remove hashtags (como `#ad`, `#promocao`) para garantir um visual limpo e premium no painel.

2. **Simulação Exata de ETA (`_refresh_queue_snapshot`)**:
   - Corrigido o cálculo do ETA que simulava burst incorretamente para filas com menos de 4 itens totais (fazia dois itens mostrarem o mesmo horário de envio).
   - Agora a simulação replica perfeitamente a tomada de decisão do worker do bot: se a quantidade restante de itens na fila após processar o item atual for `>= 3` e o burst count simulado for `< 1`, o próximo item será enviado sem delay (burst). Caso contrário, adiciona-se o delay completo (cooldown normal).

## Arquivos Alterados
- `executable/bot_runner.py`

## Resultados Esperados
- Previews dos produtos na fila limpos, objetivos e com os nomes reais do produto no Painel do Cliente.
- Prazos estimados (ETAs) de envio precisos e em perfeito sincronismo com a execução real do robô.
