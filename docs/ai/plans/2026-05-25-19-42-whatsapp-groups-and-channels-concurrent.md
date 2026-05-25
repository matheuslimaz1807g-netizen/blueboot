# Planejamento: Suporte Simultâneo a Canais e Grupos WhatsApp com Prefixação

Data/Hora: 2026-05-25 19:42
Autor: Antigravity

## Análise da Situação Atual
A pedido do cliente, havíamos restringido o envio a apenas Canais do WhatsApp. Contudo, o cliente solicitou uma nova alteração para permitir o suporte a ambas as opções simultaneamente (Grupos e Canais, ou ambos), com campos específicos e separados para cada uma no painel do cliente.

## Problemas Identificados
1. Armazenar dois tipos diferentes de destinos sem mudar a estrutura do banco de dados PostgreSQL (coluna `wpp_destinations` de tipo `JSONB` array de strings).
2. Diferenciar canais e grupos de forma confiável no painel cliente (`client_app/index.html`), painel admin central (`admin/index.html`) e painel local (`config.html`).
3. Buscar ambos os tipos no servidor WhatsApp (`server.ts`) e suportar despacho condicional e retrocompatibilidade com cadastros antigos sem prefixação.

## Soluções Propostas
- **Prefixação no Banco de Dados**: Armazenar os canais com o prefixo `channel:` (ex: `channel:Ofertas 24h`) e grupos com o prefixo `group:` (ex: `group:Grupo Promo`) na lista genérica `wpp_destinations`.
- **Desserialização/Serialização na UI**:
  - Ao carregar a configuração, filtrar itens que comecem com `channel:` e `group:` e popular os respectivos campos separados: **Canais de Destino** e **Grupos de Destino**.
  - Ao salvar, concatenar ambos os inputs com os respectivos prefixos e salvar na lista unificada.
- **Servidor WhatsApp (Node.js)**:
  - Carregar todos os chats (tanto canais quanto grupos) e identificá-los por tipo.
  - Ao despachar uma mensagem, ler o prefixo `channel:` ou `group:` para filtrar e direcionar a mensagem ao chat correto de forma 100% precisa.
  - Se um destino legado não possuir prefixo, tentar encontrar um chat com aquele nome independentemente do tipo, para manter retrocompatibilidade absoluta.

## Cronograma de Implementação
1. Ajuste do servidor WhatsApp para cachear e classificar múltiplos targets (`refreshTargets` e `sendToDestinationsInternal`) e compilação do typescript (`tsc`) - **Concluído**
2. Ajuste do Painel do Cliente (`client_app/index.html`) para apresentar inputs distintos e serializar/desserializar os prefixos - **Concluído**
3. Ajuste do Painel Admin (`admin/index.html`) para manter a mesma lógica de inputs separados e limpos - **Concluído**
4. Ajuste do Painel de Configuração Local (`config.html`) para manter conformidade total de layout e lógica - **Concluído**
5. Correção de tratamento de strings no log de depuração do Python (`pipeline.py`) usando `.startswith()` para exibir destinos amigavelmente - **Concluído**
6. Validação estática e testes de compilação - **Concluído**

## Riscos Potenciais e Mitigação
- **Risco**: Erros de digitação ou formatação de prefixo.
- **Mitigação**: Os métodos do front-end tratam com `.trim()`, removem itens nulos e ignoram prefixos brutos no input visual, gerando um payload sempre estruturado.

## Critérios de Sucesso
- Usuário final configura Canais e Grupos de forma independente na interface do cliente.
- Envio subsequente encaminha mensagens para canais, grupos ou ambos com base na seleção.
