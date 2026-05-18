# Plano: Suporte a Canais do WhatsApp

## Situação Atual
O usuário deseja que o bot do WhatsApp envie a mesma mensagem para o canal "Teste". No entanto, o `server.ts` atual dentro da pasta `Whatsapp` busca os chats usando `client.getChats()` e filtra estritamente por `c.isGroup`. 
No ecossistema da biblioteca `whatsapp-web.js`, os canais não são considerados "grupos" tradicionais. Eles são reconhecidos internamente como "newsletters" e os seus IDs de chat terminam com `@newsletter`.

## Problemas Identificados
1. **Filtro restritivo de Chats**: Canais (`@newsletter`) e Listas de Transmissão (`@broadcast`) estão sendo ignorados porque a propriedade `isGroup` retorna falso para eles.
2. **Logs Desatualizados**: O terminal registra "Total de grupos monitorados", o que pode causar confusão se estiver monitorando canais.

## Soluções Propostas
1. Modificar o filtro em `server.ts` de:
   `chats.filter((c) => c.isGroup)`
   Para:
   `chats.filter((c) => c.isGroup || c.id._serialized.includes('@newsletter') || c.id._serialized.includes('@broadcast'))`
2. Atualizar as mensagens de log de `grupos` para `grupos/canais`.

## Riscos Potenciais e Mitigação
* **Risco**: Mensagens falharem ao enviar para um canal se a conta não tiver permissão de envio no canal.
* **Mitigação**: O bloco `try/catch` atual em `sendToGroups` já previne que o loop seja quebrado, logando o erro sem interromper outros envios.

## Critérios de Sucesso
* O bot deve ser capaz de mapear o Canal "Teste" na variável `allGroups` (ou chats mapeados).
* Se "Teste" for incluído na lista de destinos (`wpp_destinations`), o servidor Node disparará a mensagem corretamente para ele.
