# Plano: Correcao das rotas de licenca para app.bluebotapp.com.br

## Analise da situacao atual

- O projeto usa FastAPI em `api/` para licencas, autenticacao, painel admin e painel cliente.
- O `client_app` usa JWT de cliente via `/auth/login/client` e consome `/client/me`, `/client/config` e `/client/logs`.
- O executavel/container gerenciado usa `executable/license.py` e `executable/main.py`, chamando rotas publicas `/license/validate`, `/license/heartbeat`, `/license/discover`, `/license/auth-code` e rotas legadas `/config/{license_key}`.
- Os logs informam `POST /license/discover 404 Not Found`, enquanto o codigo ja possui schemas e modelo para `PendingMachine`, mas nao possui router registrado para essas rotas publicas de licenca.
- As respostas 401 em `/client/*` e `/admin/*` sao esperadas quando nao ha JWT valido ou quando tokens antigos expiram; porem a ausencia das rotas `/license/*` impede o robo de aparecer/aprovar no painel e impede o app de completar o fluxo operacional.

## Problemas identificados

1. **Critico: `/license/discover` inexistente**
   - Impacto: maquinas sem `LICENSE_KEY` nao entram em pendencia no painel; o robo fica preso tentando registrar.
   - Esforco: medio.

2. **Critico: `/license/validate` e `/license/heartbeat` nao estao expostos**
   - Impacto: mesmo apos aprovacao/licenca, o executavel nao valida nem atualiza status/QR.
   - Esforco: medio.

3. **Alto: `/license/auth-code` ausente**
   - Impacto: o bot nao coleta codigo/senha enviados pelo painel admin para autenticacao Telegram.
   - Esforco: baixo-medio.

4. **Alto: rotas legadas `/config/{key}` ausentes**
   - Impacto: o executavel tenta ler/atualizar config remota por chave em fluxos de fallback/autenticacao.
   - Esforco: medio.

## Solucoes propostas

### Opcao A: adicionar um router publico `license.py`

- Pros: separa responsabilidade, preserva contratos ja usados pelo executavel, evita mexer nos routers admin/client.
- Contras: adiciona um novo arquivo e exige registro em `main.py`.
- Decisao: escolhida por ser a menor mudanca coerente com a arquitetura atual.

### Opcao B: colocar as rotas em `admin.py`

- Pros: menos arquivos.
- Contras: mistura rotas publicas com rotas protegidas de admin, aumenta acoplamento.
- Decisao: rejeitada.

## Cronograma de implementacao

1. Criar testes de integracao cobrindo 404 atual das rotas publicas.
2. Implementar router `api/app/routers/license.py` com:
   - `POST /license/discover`
   - `POST /license/validate`
   - `POST /license/heartbeat`
   - `GET /license/auth-code`
   - `GET /config/{license_key}`
   - `PUT /config/{license_key}`
3. Registrar o router no `api/app/main.py`.
4. Rodar testes focados e, se possivel, validacao importando a aplicacao.
5. Documentar a sessao em `docs/ai/changes/`.

## Riscos e mitigacao

- **Expor rotas publicas sensiveis**: manter validacao por `INSTALL_TOKEN` no discovery e por `license_key + machine_id` nas demais rotas.
- **Quebra de contratos do executavel**: manter os nomes e formatos que `executable/main.py` e `executable/license.py` ja esperam.
- **Config vazia causar erro**: usar `config_service.get_or_create_config` quando necessario.
- **Pendencia duplicada**: usar upsert manual por `machine_id`, atualizando `last_seen`.

## Criterios de sucesso

- `POST /license/discover` retorna 200 e cria/atualiza `PendingMachine`.
- Se uma licenca ja estiver vinculada ao `machine_id`, `discover` retorna `assigned_key`.
- `POST /license/validate` retorna payload assinado compativel com o cliente.
- `POST /license/heartbeat` atualiza `last_heartbeat`, status e QR do WhatsApp.
- `GET /license/auth-code` entrega e limpa codigo/senha pendentes da licenca correta.
- Rotas `/config/{license_key}` funcionam para leitura/atualizacao por chave e maquina autorizada.
