# Mudancas: correcao de envio para canal WhatsApp

## Mudancas realizadas

- Adicionado patch runtime em `Whatsapp/server.ts` e `Whatsapp/server.js` para instalar fallback `avParams` no modelo interno de mensagem do WhatsApp Web quando esse metodo nao existir.
- O patch e aplicado no evento `ready`, antes de atualizar a lista de grupos/canais.
- O envio agora contabiliza `successCount` e `failureCount` por lote.
- Quando todos os destinos encontrados falham, a fila registra erro em vez de imprimir apenas `Envio concluido`.
- Adicionado teste de regressao em `Whatsapp/tests/whatsapp-server-regression.test.js`.
- Registrado backup em `docs/ai/backups.md`.

## Razao para cada mudanca

- O erro `msg.avParams is not a function` acontece no caminho de envio de midia para canais do `whatsapp-web.js` 1.34.7.
- A biblioteca usa esse metodo para montar metadados de midia no envio para newsletter/canal; em algumas versoes atuais do WhatsApp Web, o modelo criado nao expoe a funcao.
- O fallback reaproveita `toJSON()`, `mediaData` e campos conhecidos de midia para fornecer os dados esperados sem editar `node_modules`.
- A contabilizacao por destino evita falso positivo quando a mensagem nao chegou a nenhum canal/grupo.

## Testes adicionados/modificados

- `Whatsapp/tests/whatsapp-server-regression.test.js`
  - Verifica existencia do patch de compatibilidade.
  - Verifica uso de fallback `avParams` baseado em `mediaData`.
  - Verifica contabilizacao de sucessos/falhas.
  - Verifica erro agregado quando todos os destinos falham.

## Validacao executada

- `node .\tests\whatsapp-server-regression.test.js`
- `node --check .\server.js`

## Impacto na aplicacao

- Envios para grupos seguem pelo fluxo original de `client.sendMessage`.
- Envios para canais com imagem passam a ter fallback de metadados para evitar a falha em `msg.avParams`.
- Logs da fila ficam mais confiaveis para operacao.

## Proximos passos recomendados

- Rebuild/restart do container `whatsapp_apenaspromo` para carregar o novo `server.js`.
- Testar um post real no canal `Apenas PROMO - Ofertas 24h`.
- Se o WhatsApp Web mudar novamente a API interna de canais, considerar fixar uma versao conhecida da biblioteca ou criar um patch versionado via pacote proprio.
