# Plan: Remover Cooldown Duplicado no Servidor WhatsApp

## Problema
O container do WhatsApp (`whatsapp_matheus`) está segurando as mensagens em um cooldown de 15 minutos (anti-ban redundante), ignorando o delay de 3 minutos configurado pelo cliente no painel do bot. Isso ocorre porque o arquivo compilado `server.js` estava desatualizado em relação ao arquivo `server.ts` (onde a fila redundante já havia sido removida para deixar o controle de tempo 100% sob responsabilidade do motor Python).

## Solução
1. Atualizar o arquivo `Whatsapp/server.js` para remover a fila de cooldown redundante (anti-ban) e a variável `SEND_DELAY`, deixando o servidor de WhatsApp puramente como uma bridge que envia mensagens assim que o bot Python (que já respeita a configuração do usuário) as despacha.
2. Sincronizar o endpoint `/status` em `server.js` para não retornar `next_delay_min`, alinhando-o perfeitamente com `server.ts`.

## Arquivos Alterados
- `Whatsapp/server.js`
