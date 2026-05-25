# Mudancas: autonomia do cliente, controle do bot e ajustes de console

## Mudancas realizadas

- Adicionado campo remoto `bot_enabled` em `client_configs`.
- Criada migration Alembic `011_add_bot_enabled.py` com default inicial `true`.
- Atualizados `ConfigIn` e `ConfigOut` para trafegar `bot_enabled`.
- Atualizado `config_service` para persistir e retornar `bot_enabled`.
- Ajustado `/client/config` para preservar `whatsapp_endpoint` existente ao salvar pelo painel do cliente.
- Ajustado `executable/main.py` para:
  - respeitar `bot_enabled` no start inicial;
  - monitorar `bot_enabled` no watcher remoto;
  - parar o bot quando o painel solicitar stop;
  - iniciar o bot quando o painel solicitar start e houver `api_id`/`api_hash`.
- Painel cliente atualizado com:
  - controle Startar Bot / Stop do Bot;
  - campos de API ID, API Hash e telefone;
  - tokens Shopee, AliExpress e Mercado Livre;
  - ML Cookies;
  - delay em minutos;
  - toggles de conversao e envio;
  - logs com niveis `info`, `success`, `warning` e `error`.
- Console admin corrigido:
  - cabecalho `Cliente` adicionado;
  - `colspan` do estado vazio ajustado para 9 colunas.
- Testes estaticos atualizados para cobrir:
  - autonomia do cliente sem endpoint WhatsApp;
  - controle Start/Stop;
  - contrato `bot_enabled`;
  - colunas do painel admin.

## Razao das mudancas

- Dar autonomia operacional ao cliente sem expor a configuracao sensivel do endpoint WhatsApp.
- Reutilizar o canal de configuracao remota ja existente, evitando uma arquitetura paralela de comandos.
- Melhorar a legibilidade do console admin e remover desalinhamento de colunas.
- Aumentar a visibilidade dos logs do bot no painel do cliente.

## Testes adicionados/modificados

- `api/tests/test_client_app_static.py`
- `api/tests/test_admin_panel_static.py`
- `api/tests/test_config_service.py`

## Validacao executada

- `node --check` nos scripts inline extraidos de `client_app/index.html` e `admin/index.html`: passou.
- `python -m py_compile` nos arquivos Python alterados principais: passou.

## Validacao bloqueada

- `pytest` nao esta instalado no ambiente local nem no runtime Python empacotado.
- `python`/`pytest` do sistema nao estao no PATH, e `py` retornou acesso negado.

## Impacto na aplicacao

- Clientes passam a conseguir alterar credenciais e controle do bot no painel SaaS.
- O endpoint WhatsApp permanece administrado pelo backend/admin.
- Bots existentes continuam ligados por default apos migration.
- O Start/Stop remoto aplica no ciclo do watcher, com latencia esperada de ate 30 segundos.

## Proximos passos recomendados

- Instalar dependencias de teste no ambiente de CI/local e rodar a suite completa.
- Aplicar a migration Alembic no ambiente de homologacao antes do deploy.
- Validar com um bot gerenciado real o ciclo: Stop no painel, heartbeat, Start no painel, watcher reiniciando.
