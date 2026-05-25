# Planejamento: Remoção de Envio para Grupos WhatsApp (Apenas Canais)

Data/Hora: 2026-05-25 19:45
Autor: Antigravity

## Análise da Situação Atual
O BlueBot possuía suporte a envio de ofertas/mensagens tanto para Grupos quanto para Canais (Newsletters/Broadcasts) do WhatsApp. Contudo, o cliente solicitou a remoção da função de envio para Grupos, mantendo exclusivamente o envio para Canais do WhatsApp.

## Problemas Identificados
1. O backend Node.js (`server.ts` e `server.js`) possuía a função `refreshGroups` que buscava e gerenciava grupos e canais indiferenciadamente.
2. O script Python `pipeline.py` e a classe `BotRunner` usavam logs, comentários e terminologias de "grupos/destinos" que misturavam canais e grupos.
3. O painel admin (`admin/index.html`) e o painel cliente (`client_app/index.html`) usavam placeholders e labels como "Grupos de Destino WhatsApp" ou "Destinos WhatsApp (Grupo 1, Canal 1)".

## Soluções Propostas
- **Backend Node.js**: Renomear `refreshGroups` para `refreshChannels` e ajustar o filtro para excluir qualquer chat que seja grupo (`c.isGroup === true`), aceitando apenas canais (newsletters/broadcasts).
- **Scripts Python**: Ajustar logs e mensagens informativas de "Grupos" para "Canais".
- **Interfaces Web**: Atualizar as labels e placeholders em `admin/index.html`, `client_app/index.html` e `config.html` para refletirem exclusivamente "Canais de Destino" e remover referências a grupos.

## Cronograma de Implementação
1. Modificação do Backend (`Whatsapp/server.ts` e `server.js`) - **Concluído pelo subagente**
2. Modificação do script Python (`executable/pipeline.py`) - **Concluído**
3. Ajuste do template local (`executable/web/templates/config.html`) - **Concluído**
4. Ajuste do app cliente (`client_app/index.html`) - **Concluído**
5. Ajuste final no admin central (`admin/index.html`) - **Pendente**
6. Atualização de logs em `executable/bot_runner.py` - **Pendente**
7. Validação e Testes finais - **Pendente**

## Riscos Potenciais e Mitigação
- **Risco**: Caso o usuário configure um nome de grupo no campo de destinos, a mensagem falhará silenciosamente ou retornará erro de chat não encontrado.
- **Mitigação**: Mensagens explicativas e placeholders bem claros na UI indicando que apenas canais são aceitos, além de logs claros de erro informando que o canal não foi localizado.

## Critérios de Sucesso
- Apenas canais do WhatsApp são buscados e cacheados pelo servidor.
- Mensagens de logs não fazem menção a grupos para o fluxo do WhatsApp.
- Interface visual atualizada sem menções a grupos WhatsApp.
