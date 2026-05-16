# Mudancas: log de atividades visivel ao cliente

## Mudancas realizadas

- `client_app/index.html` voltou a exibir apenas niveis `success` e `error`, ocultando `info` e `warning` tecnicos.
- `executable/main.py` separou logs locais de atividades remotas:
  - `add_log()` registra somente no log local do bot.
  - `add_client_activity_log()` alimenta a fila enviada ao painel SaaS.
- `executable/bot_runner.py` agora gera atividade de cliente quando um produto e processado e enviado:
  - `1 produto enviado para Telegram/WhatsApp. Total hoje: N.`
- `BotRunner` recebeu `activity_callback` opcional, mantendo compatibilidade com `bot_runner_vps.py`.
- Adicionados/ajustados testes estaticos:
  - `api/tests/test_client_app_static.py`
  - `api/tests/test_executable_log_forwarding_static.py`
  - `api/tests/test_bot_runner_activity_static.py`

## Razao

O painel do cliente estava mostrando detalhes operacionais como QR, polling, licenca, endpoint e debug de WhatsApp. Essas informacoes sao uteis para suporte, mas nao fazem sentido para cliente final. O painel deve exibir resultado de negocio: produtos enviados e contagem diaria.

## Validacao

- `python -m py_compile executable/main.py executable/bot_runner.py api/tests/test_client_app_static.py api/tests/test_executable_log_forwarding_static.py api/tests/test_bot_runner_activity_static.py`
- Validacao de sintaxe JavaScript do script em `client_app/index.html` via Node.
- Check estatico confirmou `allowedLevels = ['success', 'error']`.

## Impacto

- Logs tecnicos continuam disponiveis no container/painel local do bot.
- Painel SaaS do cliente passa a receber apenas atividades de negocio.
- Registros antigos `info/warning` deixam de aparecer no painel por filtro frontend.

## Proximos passos

- Fazer deploy/rebuild do bot para aplicar a separacao da fila remota.
- Atualizar o painel cliente para aplicar o filtro visual.
