# Mudança: Correção de CORS e Erro 500 em /client/config

## Data

2026-05-11 11:21

## Arquivos Modificados

### 1. `api/app/core/dependencies.py`

- **Problema**: O `get_current_license` extraía `license_id` como string do JWT (`payload.get("sub")`) e usava diretamente na query SQLAlchemy `select(License).where(License.id == license_id)`. Como a coluna `id` é `UUID(as_uuid=True)`, o SQLAlchemy com PostgreSQL async não converte string para UUID automaticamente, causando erro 500.
- **Solução**: Adicionado `import uuid` e conversão explícita `uuid.UUID(license_id)` com tratamento de exceção antes de usar na query.
- **Impacto**: Corrige o erro 500 em todos os endpoints que dependem de `get_current_license` (`/client/config`, `/client/me`, `/client/logs`, `/client/whatsapp/qr`).

### 2. `api/app/main.py`

- **Problema**: Quando ocorria uma exceção não tratada (como o erro 500 acima), o CORSMiddleware do FastAPI não adicionava headers CORS na resposta de erro, fazendo o navegador interpretar como bloqueio CORS.
- **Solução**: Adicionado middleware HTTP (`add_cors_headers_on_error`) que:
  - Captura exceções não tratadas e retorna JSON 500 com headers CORS
  - Adiciona headers CORS em respostas com status >= 400 (quando o CORSMiddleware não adicionou)
- **Impacto**: Headers CORS presentes em todas as respostas, inclusive erros.

### 3. `nginx.conf`

- **Problema**: O nginx não adicionava headers CORS nas respostas da API, então quando a API retornava erro sem headers CORS, não havia fallback.
- **Solução**: Adicionado no bloco `api.bluebotapp.com.br`:
  - Headers CORS (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, etc.) em todas as respostas
  - Tratamento de requisições OPTIONS (preflight CORS)
  - Regex para validar origins permitidas
- **Impacto**: Fallback CORS no nginx para qualquer resposta da API.

## Razão das Mudanças

O erro 500 ocorria porque o JWT do cliente armazena o `sub` como string (`str(lic.id)`), mas a query SQLAlchemy esperava um objeto `uuid.UUID`. O erro CORS era consequência do erro 500, pois o CORSMiddleware do FastAPI não adiciona headers em respostas de exceções não tratadas.

## Testes

- [ ] Verificar se `GET /client/config` retorna 200 com token válido
- [ ] Verificar se headers CORS estão presentes em respostas de erro
- [ ] Verificar se requisições OPTIONS funcionam (preflight)
- [ ] Verificar login completo do cliente (login → carregar dashboard)

## Próximos Passos Recomendados

1. Fazer deploy das alterações nos containers Docker
2. Testar o fluxo completo no ambiente de produção
3. Monitorar logs da API para confirmar que não há mais erros 500
