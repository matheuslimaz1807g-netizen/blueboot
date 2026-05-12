# Plano: Restaurar e Corrigir Client App

## Data: 2026-05-12 15:23

## Situação Atual

O arquivo `client_app/index.html` foi sobrescrito com uma versão que:
1. Removeu o login real com license_key + password (que usava a API `/auth/login/client`)
2. Substituiu por um login fictício (admin/123) sem conexão com o backend
3. Quebrou o encoding do arquivo (salvou como UTF-16 com BOM em vez de UTF-8)
4. Perdeu todo o dashboard funcional com cards de status, configurações e logs

## Problemas Identificados

### [CRÍTICO] Login fictício substituiu o real
- **Onde**: `client_app/index.html` - função `doLogin()`
- **O que**: Agora usa `admin/123` hardcoded em vez de chamar a API
- **Impacto**: Cliente não consegue acessar o painel com a licença dele

### [CRÍTICO] Encoding UTF-16 quebra JavaScript
- **Onde**: Arquivo inteiro
- **O que**: Foi salvo como UTF-16 LE com BOM em vez de UTF-8
- **Impacto**: `Uncaught SyntaxError: Invalid or unexpected token` + `tailwind is not defined`

### [ALTO] Dashboard removido
- **Onde**: Seção pós-login
- **O que**: Perdeu os cards de status (WhatsApp, último sinal, expiração), seção de config e logs
- **Impacto**: Cliente não vê informações da licença dele

### [MÉDIO] API base incorreta
- **Onde**: `apiBase` no JavaScript
- **O que**: Versão original usava `https://api.bluebotapp.com.br`, versão atual não tem
- **Impacto**: Chamadas de API não funcionam

## Solução Proposta

**Abordagem**: Restaurar a versão do commit `34168e7` (última versão funcional) e garantir encoding UTF-8 correto.

### Passos:

1. **Fazer backup** do estado atual com `git stash`
2. **Restaurar** o arquivo do commit `34168e7` via `git checkout 34168e7 -- client_app/index.html`
3. **Corrigir encoding**: Garantir que está UTF-8 sem BOM usando Python
4. **Testar localmente**: Abrir no navegador e verificar se não há erros no console
5. **Commitar e subir** para o GitHub

### Riscos e Mitigação

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Encoding quebrar de novo | Média | Usar Python para salvar, não write_to_file |
| Perder alterações do commit 9a16f69 | Baixa | O commit 34168e7 é anterior, mas tem o login real |
| API não responder | Baixa | O frontend já trata erros de conexão |

### Critérios de Sucesso

- [ ] Login funciona com license_key + password via API
- [ ] Dashboard exibe cards de status corretamente
- [ ] Nenhum erro no console do navegador
- [ ] Arquivo em UTF-8 sem BOM
- [ ] `tailwind is not defined` não aparece mais
