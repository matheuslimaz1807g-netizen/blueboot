# Mudanças Realizadas: Suporte a Canais do WhatsApp

**Data/Hora**: 2026-05-18 19:35

## Mudanças Realizadas
1. **Atualização do Filtro de Chats (`server.ts`)**: Modificada a função de mapeamento inicial do `whatsapp-web.js` para não filtrar exclusivamente por `c.isGroup`. Adicionado filtro extra `c.id._serialized.includes('@newsletter')` e `@broadcast`.
2. **Atualização de Log (`server.ts`)**: Modificados os textos de `console.log` e de mensagens de erro de "grupos" para "grupos/canais" a fim de manter coerência nas rotinas de monitoramento e debug.

## Razão para Cada Mudança
- O usuário precisava que o bot disparasse a mesma mensagem para um Canal ("Teste"). Como a API do `whatsapp-web.js` trata Canais como *Newsletters* (onde a propriedade `isGroup` é falsa), eles não eram listados em `allGroups`, impossibilitando o envio, mesmo que as configurações (`wpp_destinations`) estivessem corretas. A mudança corrige a detecção para contemplar grupos e canais simultaneamente.

## Testes Adicionados/Modificados
- N/A. (Não há suíte de testes automatizados unitários no servidor `server.ts` do módulo WhatsApp).

## Impacto na Aplicação
- O bot passa a ter total capacidade de buscar, reconhecer e mapear Canais do WhatsApp nos quais o número está inscrito. Se uma string contendo o nome do Canal for enviada no parâmetro `targets` do payload da rota POST `/send`, a mensagem será disparada com sucesso para esse canal também.

## Próximos Passos Recomendados
- Instruir o usuário a adicionar o termo "Teste" (ou o nome exato do canal) na variável `wpp_destinations` através da plataforma.
- Caso existam instabilidades nas dependências de tipagem (ex: TS7006 parameter `c` any types), é recomendado posteriormente rodar `npm install` e ajustar a tipagem restrita caso o strict mode do TS comece a barrar novos builds na pipeline.
