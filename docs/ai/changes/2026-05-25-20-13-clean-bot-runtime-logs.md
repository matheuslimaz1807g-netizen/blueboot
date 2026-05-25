# Mudancas: limpeza de logs operacionais do bot

## Mudancas realizadas

- Adicionada rota `/health` no Flask local do executavel.
- Desabilitado o logger `werkzeug` no executavel para remover access logs de requests.
- `config_loader` deixou de imprimir configuracao local/remota por padrao.
- Criado opt-in `BLUEBOT_VERBOSE_CONFIG=true` para reativar logs de config em diagnostico.
- Removido heartbeat repetitivo `Heartbeat: Bot monitorando...` do `BotRunner`.
- Removido log recorrente `ML_COOKIES sincronizado: XXXX caracteres`.
- Adicionado teste estatico para proteger a higiene de logs.

## Razao

Os logs do container estavam sendo dominados por eventos tecnicos repetitivos, como healthcheck 404, access log HTTP, merge de config a cada watcher, heartbeat e sincronizacao de cookies. Isso escondia os eventos relevantes do bot.

## Testes adicionados/modificados

- `api/tests/test_executable_log_forwarding_static.py`

## Validacao executada

- `python -m py_compile` em:
  - `executable/main.py`
  - `executable/config_loader.py`
  - `executable/bot_runner.py`
  - `api/tests/test_executable_log_forwarding_static.py`
- Checagem estatica via Node REPL confirmando:
  - `/health` presente;
  - `werkzeug` desabilitado;
  - `BLUEBOT_VERBOSE_CONFIG` presente;
  - ausencia de `Config Mesclada`;
  - ausencia de `Heartbeat: Bot monitorando`;
  - ausencia de `ML_COOKIES sincronizado`.

## Validacao bloqueada

- `pytest` segue indisponivel no ambiente local.

## Impacto

- `GET /health` passa a retornar 200 e nao gerar 404.
- Docker logs ficam focados em eventos relevantes.
- Config remoto continua sendo buscado/aplicado normalmente.
- Diagnostico detalhado de config ainda pode ser habilitado com `BLUEBOT_VERBOSE_CONFIG=true`.
