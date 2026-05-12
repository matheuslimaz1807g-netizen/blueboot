# Plano: Correção da Persistência de Sessão do Telegram

## Data: 2026-05-12

## Situação Atual

Ao reiniciar o container Docker (`docker restart bot_matheus`), o bot sempre solicita nova autenticação do Telegram porque a `session_string` não é persistida localmente.

## Causa Raiz

1. **`main.py`** (linhas 392-410): Quando a autenticação ocorre via polling do painel, a `session_string` é enviada apenas para a API remota, **nunca salva no `.env` local**.
2. **`main.py`** (endpoint `/api/auth-code`): Quando a autenticação é feita manualmente pelo dashboard, a `session_string` é retornada na resposta mas **não é salva em lugar nenhum**.
3. **`config_loader.py`** (linha 45): Carrega `TELEGRAM_SESSION_STRING` do `.env` via `os.getenv()`. Como o `.env` nunca é atualizado, a session fica vazia após restart.
4. **`merge_configs`**: Se a API remota estiver indisponível, o fallback é a config local (`.env`), que está vazia.

## Solução Proposta

### 1. Criar função utilitária `save_session_to_env()`

Função que atualiza a variável `TELEGRAM_SESSION_STRING` no arquivo `.env`:

- Lê o `.env` atual
- Substitui ou adiciona `TELEGRAM_SESSION_STRING=<nova_session>`
- Salva o arquivo

### 2. Modificar `main.py` — Salvar session_string no `.env` após autenticação

**No polling de autenticação** (função `poll_auth_code`, ~linha 392):
- Após receber `session_str` com sucesso, chamar `save_session_to_env(session_str)`

**No endpoint `/api/auth-code`** (~linha 158-173):
- Após `_runner.submit_code()` retornar `ok=True`, chamar `save_session_to_env(session_str)`

### 3. Garantir que o `.env` esteja acessível para escrita no container

O `Dockerfile.bot` já copia o `.env` para `/app/.env`. Precisamos garantir que o container possa escrever nele.

## Arquivos Modificados

- `executable/main.py` — Adicionar função `save_session_to_env()` e chamadas nos pontos de autenticação

## Testes

1. Fazer deploy, autenticar via painel
2. Executar `docker restart bot_matheus`
3. Verificar se o bot reconecta sem pedir código
4. Verificar se o `.env` foi atualizado com `TELEGRAM_SESSION_STRING`

## Riscos

- O `.env` pode não ser writable no container se montado como read-only
- Se o `.env` não existir, precisamos criar
- A session string pode conter caracteres especiais que precisam de escaping no `.env`
