# Mudança: Restauração do Client App

## Data: 2026-05-12 15:26

## Commits
- `50db040` - Restaura versão funcional do commit 34168e7 com login real via API + encoding UTF-8 sem BOM
- `49e5fc6` - Remove arquivos temporários

## O que foi feito

### Problema
O `client_app/index.html` havia sido sobrescrito com:
1. Login fictício (admin/123) em vez do real com license_key + password via API
2. Encoding UTF-16 com BOM que quebrava o JavaScript
3. Dashboard removido (sem cards de status, config e logs)

### Solução
1. Restaurado o conteúdo do commit `34168e7` (última versão funcional)
2. Convertido o encoding de UTF-16 LE com BOM para UTF-8 sem BOM
3. Normalizados os line endings (\r\r\n -> \n)
4. Removidos arquivos temporários do commit

### Arquivos modificados
- `client_app/index.html` - Restaurado e com encoding corrigido
- `docs/ai/plans/2026-05-12-15-23-restaurar-client-app.md` - Plano criado

### Funcionalidades restauradas
- Login com Chave de Licença + Senha via API `/auth/login/client`
- Dashboard com cards de status (WhatsApp, último sinal, expiração)
- Seção de configurações (destino Telegram, fontes monitoradas)
- Seção de logs de atividade
- JWT armazenado no localStorage
- Auto-refresh a cada 30 segundos

### Próximos passos
- Fazer deploy no servidor (copiar para /usr/share/nginx/html/client/index.html)
- Testar no https://app.bluebotapp.com.br/app_static/
