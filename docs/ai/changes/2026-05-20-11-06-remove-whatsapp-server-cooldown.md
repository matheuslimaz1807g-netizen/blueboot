# Log de Mudanças - Remoção de Cooldown Redundante no Servidor WhatsApp

**Data**: 2026-05-20 11:06 (BRT)

## Mudanças Realizadas
1. **Sincronização entre `server.ts` e `server.js` (`Whatsapp/server.js`)**:
   - Removido o cooldown de 15 minutos (anti-ban) que estava hardcoded na fila do servidor de WhatsApp.
   - O delay entre disparos de WhatsApp deve ser controlado **exclusivamente** pelo bot em Python (que segue a configuração definida pelo cliente no Painel do Bot).
   - O container de WhatsApp passa a atuar puramente como uma bridge, enviando as mensagens imediatamente assim que são despachadas pelo robô em Python.
   - Removida a chave `next_delay_min` do endpoint `/status` para sincronizar o arquivo compilado com a versão em TypeScript.

## Arquivos Alterados
- `Whatsapp/server.js`

## Resultados Esperados
- O delay do robô passará a respeitar estritamente o tempo configurado pelo cliente (ex: 3 minutos), eliminando a espera indesejada de 15 minutos forçada pelo container do WhatsApp.
