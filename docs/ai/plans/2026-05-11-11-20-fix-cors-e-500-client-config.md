# Plano: Correção de CORS e Erro 500 em /client/config

## Análise da Situação Atual

### Problemas Identificados

1. **[CRÍTICO] Erro 500 em GET /client/config**
   - **Causa Raiz**: O endpoint `GET /client/config` depende de `get_current_license` que extrai `license_id = payload.get("sub")` do JWT. O `sub` é uma **string** (gerado como `str(lic.id)` em `auth.py:86`), mas a query SQLAlchemy compara com a coluna `License.id` que é `UUID(as_uuid=True)`. SQLAlchemy com PostgreSQL async não faz conversão automática de string para UUID, resultando em erro 500.
   - **Impacto**: Impede completamente o carregamento da página do cliente após o login.

2. **[CRÍTICO] CORS Bloqueado**
   - **Causa Raiz**: O erro 500 no endpoint faz com que o FastAPI retorne a resposta sem os headers CORS adequados (o CORSMiddleware pode não processar exceções não tratadas corretamente). O navegador então interpreta como bloqueio CORS.
   - **Impacto**: Mensagem de erro confusa para o usuário.

3. **[MÉDIO] Nginx sem headers CORS de fallback**
   - O nginx não adiciona headers CORS, então quando a API retorna erro, não há fallback.

### Soluções Propostas

#### Correção 1: Converter string UUID para objeto UUID no get_current_license

- **Arquivo**: `api/app/core/dependencies.py`
- **Mudança**: Converter `license_id` de string para `uuid.UUID` antes de usar na query.
- **Risco**: Baixo. É uma correção direta.

#### Correção 2: Adicionar CORS exception handler global no FastAPI

- **Arquivo**: `api/app/main.py`
- **Mudança**: Adicionar um middleware ou exception handler que garanta headers CORS mesmo em erros 500.
- **Risco**: Baixo. Prática recomendada.

#### Correção 3: Adicionar headers CORS no nginx para a API

- **Arquivo**: `nginx.conf`
- **Mudança**: Adicionar headers CORS no bloco da API (api.bluebotapp.com.br).
- **Risco**: Baixo. Apenas adiciona headers.

### Critérios de Sucesso

- [ ] GET https://api.bluebotapp.com.br/client/config retorna 200 com dados do config
- [ ] Headers CORS presentes em todas as respostas (inclusive erros)
- [ ] Login do cliente seguido de carregamento do dashboard funciona sem erros
