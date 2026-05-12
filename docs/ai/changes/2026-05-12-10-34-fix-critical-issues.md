# Correção de Itens Críticos da Auditoria

## Data: 2026-05-12 10:34

## Mudanças Realizadas

### 1. 🔴 Template HTML Extraído de `executable/main.py`
- **Antes**: ~400 linhas de HTML inline na variável `DASHBOARD_HTML`
- **Depois**: Template em `executable/templates/dashboard.html`, carregado via `Path.read_text()`
- **Benefício**: Syntax highlighting, versionamento, manutenção facilitada

### 2. 🔴 SSL `verify=False` Corrigido em Produção
- **Função criada**: `should_verify_ssl(url)` em `executable/utils.py`
  - URLs `http://` (Docker interno): retorna `False` (sem SSL)
  - URLs `https://` (produção): retorna `True` (verifica SSL)
  - Controlado por env var `SSL_VERIFY` (default: `true`)
- **Arquivos modificados**:
  - `executable/license.py`: 3 ocorrências de `verify=False` → `verify=should_verify_ssl(url)`
  - `executable/config_loader.py`: 2 ocorrências de `verify=False` → `verify=should_verify_ssl(url)`
  - `executable/main.py`: 4 ocorrências de `verify=False` → `verify=should_verify_ssl(url)`
- **Benefício**: Segurança contra MITM em produção

### 3. 🔴 Design Tokens Centralizados
- **Arquivo criado**: `static/css/bluebot.css`
- **Contém**: Variáveis CSS custom properties para cores, tipografia, espaçamento, bordas
- **Classes utilitárias**: `.card`, `.badge`, `.btn`, `.input`, `.table`, `.log-container`, `.flex`, etc.
- **Próximo passo**: Refatorar `admin/*.html` e `client_app/index.html` para usar o CSS centralizado

## Arquivos Modificados/Criados
- `executable/main.py` — Template extraído, SSL corrigido
- `executable/utils.py` — Funções `get_verify_ssl()` e `should_verify_ssl()` adicionadas
- `executable/license.py` — SSL corrigido, import de `should_verify_ssl`
- `executable/config_loader.py` — SSL corrigido, import de `should_verify_ssl`
- `executable/templates/dashboard.html` — **NOVO**: Template externo do dashboard
- `static/css/bluebot.css` — **NOVO**: Design tokens centralizados

## Testes Recomendados
1. Verificar se o dashboard carrega corretamente (template externo)
2. Verificar se requisições HTTPS em produção usam `verify=True`
3. Verificar se requisições HTTP internas (Docker) continuam sem verificação
