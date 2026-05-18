# Mudanças Realizadas: Adição do Destinos WhatsApp no Admin Panel e Cliente

**Data/Hora**: 2026-05-18 19:45

## Mudanças Realizadas
1. **Frontend (`admin/index.html` e `client_app/index.html`)**: Foram adicionados inputs no HTML e lógicas no Javascript interno para permitir a escrita e leitura do array `wpp_destinations` (mapeado temporariamente como `wpp_destinations_str` no frontend). O painel admin agora tem o campo explícito debaixo do Endpoint WhatsApp.
2. **Backend API (`api/app/schemas/schemas.py`)**: Incluído `wpp_destinations` no `ConfigIn` e `ConfigOut` para que a API FastAPI parseie e persista corretamente este parâmetro ao invés de descartar.
3. **Model do Banco de Dados (`api/app/models/models.py`)**: Adicionado o model MappedColumn `wpp_destinations` no tipo JSONB na tabela `client_configs`.

## Impacto na Aplicação
- A funcionalidade do frontend do Admin (e também do Cliente) agora suporta adicionar múltiplos destinos (canais ou grupos) do WhatsApp no qual a automação precisará interagir. Esta informação agora é salva em JSONB de maneira limpa junto com as URLs do Telegram no banco de dados SaaS (PostgreSQL).

## Próximos Passos Obrigatórios
- **Migração do Banco**: É estritamente necessário criar a migration no banco de produção. Acesse o servidor e execute o container:
  `docker-compose exec api alembic revision --autogenerate -m "add wpp_destinations"`
  `docker-compose exec api alembic upgrade head`
