# Plano: tornar log de atividades visivel ao cliente

## Analise da situacao atual

- O painel do cliente passou a exibir `info` e `warning`, o que ajudou no diagnostico, mas expoe detalhes tecnicos sem valor para o cliente.
- O bot envia todos os logs locais para o heartbeat central por `_pending_remote_logs`.
- O cliente precisa ver resultado de negocio: quantidade/produtos enviados, nao configuracao interna, QR, polling, licenca ou debug de WhatsApp.

## Problemas identificados

1. Logs tecnicos aparecem no painel do cliente.
2. O canal remoto de logs usa a mesma origem do log operacional local.
3. Logs antigos `info` continuam visiveis no frontend se retornados pela API.

## Solucao proposta

- Separar logs locais de logs de atividade do cliente.
- `add_log()` continua registrando tudo localmente.
- Criar `add_client_activity_log()` para a fila enviada ao heartbeat.
- Fazer o `BotRunner` publicar atividade de negocio quando uma mensagem e processada com sucesso:
  - "1 produto enviado para Telegram/WhatsApp. Total hoje: N."
- O painel do cliente volta a exibir apenas `success` e `error`, ocultando `info` e `warning` antigos.

## Riscos e mitigacao

- Risco: cliente perder visibilidade de falhas tecnicas.
  - Mitigacao: falhas continuam nos logs locais do bot; o painel cliente fica limpo.
- Risco: mudar assinatura do `BotRunner`.
  - Mitigacao: parametro opcional com fallback para manter compatibilidade com `bot_runner_vps.py`.

## Criterios de sucesso

- Logs tecnicos nao sao enviados ao heartbeat por `add_log()`.
- Atividades remotas sao geradas apenas por `add_client_activity_log()`.
- Painel cliente filtra somente `success` e `error`.
- Sintaxe Python e JavaScript valida.
