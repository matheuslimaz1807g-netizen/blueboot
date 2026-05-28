# Plano de Implementação — Integração Completa do Módulo Amazon no Projeto BlueBot

Este plano estabelece a estratégia detalhada para integrar a funcionalidade da Amazon (geração automatizada de links de afiliado usando SiteStripe/Selenium) no ecossistema BlueBot, estendendo-a à API REST (banco de dados/criptografia) e às interfaces visuais (Painel Admin e Painel do Cliente).

---

## 1. Análise da Situação Atual e Problemas

Atualmente, o projeto possui o módulo síncrono/assíncrono `amazon.py` que executa com sucesso a automação no navegador Brave/Chrome para obter links de afiliado via SiteStripe bar. No entanto, sua integração com as demais camadas do projeto está incompleta ou ausente:

1. **Local Bot Config**:
   - `config_loader.py` lê as chaves `conv_amz` e `amz_cookies` do `.env`.
   - `pipeline.py` detecta links Amazon e executa a conversão se `conv_amz` estiver ativado.
   - **Problema**: `conv_amz` é `false` por padrão e não está exposto ao usuário de forma transparente nas configurações remotas e interfaces.

2. **API (Banco de Dados, Schemas e Serviços)**:
   - O modelo `ClientConfig` do SQLAlchemy possui propriedades para Shopee, AliExpress e Mercado Livre, mas **não possui** `conv_amz` nem o campo criptografado para cookies `amz_cookies_enc`.
   - Os schemas Pydantic `ConfigIn` e `ConfigOut` não contêm os campos `conv_amz` e `amz_cookies`.
   - O serviço `config_service.py` não descriptografa nem criptografa os cookies da Amazon na hora de salvar e obter as configurações da licença.

3. **Painel do Cliente (`client_app/index.html`)**:
   - Possui campos para Shopee, AliExpress e Mercado Livre, mas não exibe controles da Amazon (Toggle "Converter Amazon" nem input para os Cookies de Autenticação).

4. **Painel Admin (`admin/index.html`)**:
   - O painel administrativo não expõe chaves ou cookies da Amazon para a licença, impedindo a visualização da configuração e diagnósticos centralizados.

---

## 2. Soluções Propostas

Propomos uma expansão simétrica aos outros módulos de afiliados (como Shopee e Mercado Livre):

### A. Banco de Dados & API (Camada Backend)
1. **Modelos (`api/app/models/models.py`)**:
   - Adicionar campo `conv_amz: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)`
   - Adicionar campo `amz_cookies_enc: Mapped[str | None] = mapped_column(Text, nullable=True)`
2. **Schemas (`api/app/schemas/schemas.py`)**:
   - Adicionar `conv_amz: bool = True` e `amz_cookies: str | None = None` em `ConfigIn`.
   - Adicionar `conv_amz: bool` e `amz_cookies: str | None` em `ConfigOut`.
3. **Serviço (`api/app/services/config_service.py`)**:
   - Mapear a leitura em `get_config`: `amz_cookies=decrypt_field(cfg.amz_cookies_enc) if cfg.amz_cookies_enc else None` e `conv_amz=cfg.conv_amz`.
   - Mapear o salvamento em `upsert_config`: criptografar `amz_cookies` em `amz_cookies_enc` e salvar o booleano `conv_amz`.
4. **Migração do Banco**:
   - Criar arquivo de migração do Alembic adicionando as colunas `conv_amz` (com default `true`) e `amz_cookies_enc` (nullable) na tabela `client_configs`.

### B. Interface do Painel do Cliente (`client_app/index.html`)
1. **Inputs de Credenciais**:
   - Adicionar campo Textarea de "Amazon Cookies" na seção de Credenciais de Afiliado.
2. **Opções de Operação (Toggles)**:
   - Adicionar um toggle de checkbox `Converter Amazon` na seção "Configurações de Operação".

### C. Interface do Painel Admin (`admin/index.html`)
1. **Controles na modal de Configuração**:
   - Garantir que o painel possua o controle ou visualização da Amazon nas licenças de forma condizente.

### D. Documentação
1. Adicionar `CONV_AMZ=true` e `AMZ_COOKIES=` no `.env.example` na raiz do projeto.

---

## 3. Cronograma de Implementação

- **Etapa 1**: Execução do Backup usando `git stash`.
- **Etapa 2**: Alterar arquivos backend da API (`models.py`, `schemas.py`, `config_service.py`).
- **Etapa 3**: Criar e aplicar script de migração Alembic.
- **Etapa 4**: Atualizar o Painel do Cliente (`client_app/index.html`) para expor toggle e input de cookies.
- **Etapa 5**: Atualizar o Painel Admin (`admin/index.html`) para sincronia se necessário.
- **Etapa 6**: Atualizar arquivo `.env.example`.
- **Etapa 7**: Validar e Documentar mudanças em `/docs/ai/changes/`.

---

## 4. Riscos Potenciais e Mitigação

- **Risco**: Incompatibilidade da migração do banco com registros existentes.
  - *Mitigação*: Definir valor default para `conv_amz` como `True` de forma retroativa e permitir `amz_cookies_enc` como nulo.
- **Risco**: Quebra de tipos no JSON mapeado nas rotas REST.
  - *Mitigação*: Atualizar estritamente os esquemas Pydantic garantindo tipagem consistente (`bool` e `str | None`).

---

## 5. Critérios de Sucesso

1. A API aceita a propriedade `conv_amz` e `amz_cookies` nas requisições `PUT /client/config`.
2. As credenciais dos cookies da Amazon são armazenadas de forma criptografada (`amz_cookies_enc`) usando a chave Fernet do projeto.
3. O painel do cliente carrega a configuração atual da Amazon e permite alterá-la com sucesso.
4. O arquivo `.env.example` documenta a configuração local da Amazon.
