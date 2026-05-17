# Mudancas: deduplicacao de produtos entre fontes

## Mudancas realizadas

- Adicionada assinatura de produto em `executable/bot_runner.py` com `_product_fingerprint()`.
- Adicionada memoria de produtos pendentes e recentes:
  - `_pending_product_fingerprints`;
  - `_recent_product_fingerprints`;
  - `_recent_product_order`.
- Antes de entrar na fila de envio, cada mensagem agora passa por `_remember_product()`.
- Se o mesmo produto ja estiver pendente ou tiver sido enviado recentemente, ele e ignorado antes de ocupar a fila.
- A assinatura pendente e liberada quando o worker conclui o processamento.
- Produtos realmente enviados ficam na memoria recente por 24 horas.
- Atualizado `api/tests/test_bot_runner_activity_static.py` para proteger a deduplicacao.

## Razao para cada mudanca

- A deduplicacao anterior era por `(chat_id, msg_id)`, suficiente para uma fonte, mas insuficiente para fontes como `t.me/lobaopromo` e `t.me/pobregram` publicando a mesma oferta.
- Sem dedupe por produto, a fila de 10 minutos poderia conter duplicatas e reenviar a mesma promocao.

## Testes adicionados/modificados

- Adicionado teste estatico para garantir:
  - existencia de `_product_fingerprint()`;
  - existencia de `_remember_product()`;
  - existencia de `_finish_product()`;
  - TTL de 24 horas;
  - enfileiramento com `(fingerprint, message)`;
  - log de duplicata antes da fila.

## Validacao executada

- `python -m py_compile executable/bot_runner.py api/tests/test_bot_runner_activity_static.py`.
- Assercoes estaticas via Node para confirmar a presenca da deduplicacao e ausencia do envio paralelo antigo.

## Impacto na aplicacao

- Se duas fontes publicarem o mesmo produto, apenas a primeira mensagem entra na fila.
- O bot continua monitorando todas as fontes normalmente.
- A fila fica mais limpa e o WhatsApp recebe menos mensagens repetidas.

## Proximos passos recomendados

- Fazer commit/push desta mudanca junto com a fila de 10 minutos, caso ainda nao tenha sido enviado.
- Rebuild/redeploy na VPS e acompanhar logs `[Dedup]` e `[RateLimit]`.
