# Plano: Correção de Itens Críticos da Auditoria

## Data: 2026-05-12 10:34

## Itens a Corrigir

### 1. 🔴 Extrair Templates HTML de `executable/main.py`
- **Problema**: `main.py` contém ~400 linhas de HTML inline (dashboard, etc.)
- **Solução**: Criar diretório `executable/templates/` com arquivos `.html` separados
- **Arquivos**: `dashboard.html`, `login.html`, `status.html`
- **Impacto**: Manutenibilidade, versionamento, syntax highlighting

### 2. 🔴 SSL `verify=False` em Produção
- **Problema**: `requests.get/post(..., verify=False)` em `license.py`, `config_loader.py`, `main.py`
- **Solução**: 
  - Criar função `get_verify_ssl()` que retorna `True` em produção, `False` em dev
  - Usar variável de ambiente `SSL_VERIFY` (default: `true`)
  - Manter `verify=False` apenas para endpoints locais (Docker internal)
- **Impacto**: Segurança contra MITM

### 3. 🔴 Centralizar Design Tokens
- **Problema**: Cores e estilos duplicados em `admin/index.html`, `admin/login.html`, `admin/view.html`, `client_app/index.html`
- **Solução**: Criar `static/css/bluebot.css` com variáveis CSS custom properties
- **Impacto**: Consistência visual, facilidade de manutenção

## Ordem de Implementação
1. Backup via git stash
2. Extrair templates HTML
3. Corrigir SSL verify
4. Centralizar design tokens
5. Testar e documentar
