# Mudanca: Correcao das rotas publicas de licenca para o app BlueBot

## Mudancas realizadas

- Criado `api/app/routers/license.py` com as rotas publicas usadas pelo executavel:
  - `POST /license/discover`
  - `POST /license/validate`
  - `POST /license/heartbeat`
  - `GET /license/auth-code`
  - `GET /config/{license_key}`
  - `PUT /config/{license_key}`
- Registrado o novo router em `api/app/main.py`.
- Adicionados testes focados em `api/tests/test_public_license_routes.py`.
- Registrado backup em `docs/ai/backups.md`.
- Criado plano em `docs/ai/plans/2026-05-11-18-56-fix-rotas-license-app.md`.

## Razao para cada mudanca

- O container gerenciado estava chamando `POST /license/discover` e recebendo 404 porque a rota nao existia.
- O executavel tambem depende de `/license/validate`, `/license/heartbeat`, `/license/auth-code` e `/config/{license_key}` para completar validacao, heartbeat, QR/status WhatsApp, autenticacao Telegram e leitura de config remota.
- O router novo preserva os contratos esperados pelo executavel sem misturar rotas publicas com rotas protegidas de admin/cliente.

## Testes adicionados/modificados

- `test_public_license_routes_are_registered`: garante que as rotas publicas esperadas estao registradas.
- `test_discover_creates_pending_machine_when_unassigned`: garante que uma maquina sem licenca vinculada entra como pendente.
- `test_validate_license_returns_signed_payload`: garante que validacao retorna payload assinado.

## Validacao executada

- `python -m pytest api\tests\test_public_license_routes.py -q`
- `python -m pytest api\tests -q`
- `python -m compileall api\app`
- Importacao de `app.main` e listagem das rotas publicas de licenca registradas.

## Impacto na aplicacao

- O erro `POST /license/discover 404 Not Found` deve parar apos rebuild/redeploy da API.
- Maquinas sem `LICENSE_KEY` passam a aparecer em `/admin/pending` para aprovacao.
- Maquinas aprovadas recebem `assigned_key`, validam licenca e enviam heartbeat/status novamente.
- Os 401 em `/client/*` e `/admin/*` continuam corretos para token ausente/expirado; o usuario precisa fazer login novamente quando isso ocorrer.

## Proximos passos recomendados

- Rebuild/redeploy do container `api`.
- Reiniciar o container/servico do robo que esta tentando `/license/discover`.
- No navegador, fazer logout/login novamente no painel cliente/admin se houver tokens antigos no `localStorage`.
