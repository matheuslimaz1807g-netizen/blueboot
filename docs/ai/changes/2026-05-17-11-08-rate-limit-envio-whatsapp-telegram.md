# Mudancas: rate limit de envio WhatsApp/Telegram

## Mudancas realizadas

- Alterado `executable/bot_runner.py` para substituir envios paralelos por uma fila assíncrona unica.
- Adicionado `_DELIVERY_INTERVAL_SECONDS = 10 * 60`.
- O polling continua rodando a cada 10 segundos para capturar produtos novos, mas agora apenas enfileira as mensagens.
- Um worker unico (`_delivery_worker`) processa a fila em ordem.
- Apos envio real para Telegram ou WhatsApp, o proximo envio fica bloqueado por 10 minutos.
- Adicionados `delivery_queue_size` e `next_dispatch_seconds` nos stats do runner.
- Atualizado `api/tests/test_bot_runner_activity_static.py` com teste estatico protegendo a fila e removendo o disparo paralelo.

## Razao para cada mudanca

- O envio anterior usava `asyncio.create_task(self._process_and_count(message))` para cada mensagem nova.
- Quando muitos produtos chegavam juntos, o bot enviava varias mensagens em sequencia, com risco alto de bloqueio do WhatsApp por spam.
- A fila preserva os produtos detectados sem permitir rajadas de envio.

## Testes adicionados/modificados

- `test_bot_runner_rate_limits_product_delivery_queue` garante:
  - intervalo de 10 minutos;
  - existencia da fila;
  - existencia do worker de envio;
  - enfileiramento das mensagens;
  - ausencia do disparo paralelo antigo.

## Validacao executada

- `python -m py_compile executable/bot_runner.py api/tests/test_bot_runner_activity_static.py` usando o Python empacotado do Codex.
- Assercoes estaticas equivalentes ao teste de rate limit via `node`.

## Impacto na aplicacao

- O bot deixa de enviar varios produtos sem intervalo.
- Se chegarem muitos produtos, eles ficam aguardando em fila.
- O primeiro item disponivel pode ser enviado imediatamente; os proximos so saem apos 10 minutos de intervalo quando houve envio real para Telegram ou WhatsApp.
- Mensagens ignoradas por nao terem link convertido ou por filtro nao seguram a fila por 10 minutos.

## Riscos residuais

- A fila fica em memoria; em restart do container, itens enfileirados e ainda nao enviados podem ser perdidos.
- Se a origem publicar mais produtos do que 1 a cada 10 minutos por muito tempo, a fila vai crescer. Isso e esperado para proteger a conta do WhatsApp.

## Proximos passos recomendados

- Fazer rebuild/redeploy do bot na VPS.
- Monitorar os logs `[RateLimit]` para confirmar tamanho da fila e horario aproximado do proximo envio.
