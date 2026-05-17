# Planejamento: Correção da Fila do BotRunner

## 1. Análise da Situação Atual
O usuário relatou que o bot "continua mandando mensagem uma em seguida da outra", ignorando o atraso/fila esperado.

**Problemas Identificados**:
1. **[CRÍTICO] Timeout prematuro do WhatsApp**: O backend em Node (`server.ts`) utiliza um loop com `setTimeout` de 1.5s entre o envio de cada grupo. Se o bot for configurado para enviar para 20 grupos, a requisição levará 30 segundos. No entanto, o `pipeline.py` faz a requisição com um hard-timeout de apenas `20` segundos (`httpx.AsyncClient(timeout=20)`). Isso faz com que o Python receba um `TimeoutError` antes do Node terminar, retornando `wp_sent = False`.
2. **[CRÍTICO] Falha na ativação do Cooldown**: No `bot_runner.py`, a verificação de ativação da fila é feita através da condição `if tg_ok or wp_ok:`. Como o timeout do WhatsApp seta `wp_ok` para `False`, o cooldown é sumariamente ignorado e a próxima mensagem da fila é processada **imediatamente**.
3. **[ALTO] Delay Fixo vs Configurável**: O código do `bot_runner.py` não está usando o parâmetro configurável `self._delay` (definido no painel de controle pelo usuário). Ele está usando uma constante global engessada `_DELIVERY_INTERVAL_SECONDS = 10 * 60` (10 minutos).

## 2. Soluções Propostas
1. Em `bot_runner.py` (linha ~467): Alterar a condição de `if tg_ok or wp_ok:` para `if _processed:`. Dessa forma, desde que a mensagem seja válida e não caia em filtros, o "delay" será respeitado na fila, independente de um erro HTTP em um dos conectores.
2. Em `bot_runner.py` (linha ~469): Remover o uso da constante global `_DELIVERY_INTERVAL_SECONDS` e usar a variável do usuário `self._delay`.
3. Em `pipeline.py` (linha ~377): Aumentar o timeout da requisição pro WhatsApp de `20` para `300` segundos.

## 3. Riscos e Mitigações
- **Risco**: Um timeout de 300 segundos pode travar a thread asyncio se o servidor Node travar para sempre.
- **Mitigação**: 300 segundos é o ideal, pois permite o envio a um grande volume de grupos (~200 grupos) antes de falhar, mas é seguro o suficiente para não travar de forma infinita a aplicação.
