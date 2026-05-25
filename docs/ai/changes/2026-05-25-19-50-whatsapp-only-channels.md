# Log de Mudanças: Remoção de Envio para Grupos WhatsApp (Apenas Canais)

Data/Hora: 2026-05-25 19:50
Autor: Antigravity

## Mudanças Realizadas

### 1. Servidor WhatsApp (Node.js)
- **`Whatsapp/server.ts` & `Whatsapp/server.js`**:
  - Renomeada a função `refreshGroups` para `refreshChannels`.
  - Renomeada a variável global `allGroups` para `allChannels`.
  - Adicionado filtro explícito para remover qualquer chat que seja grupo (`c.isGroup === true`), garantindo que apenas newsletters e broadcasts (canais) sejam aceitos.
  - Renomeada a função de envio sequencial `sendToGroupsInternal` para `sendToChannelsInternal`.
  - Atualizados todos os logs e mensagens de erro no console para usar o termo "canais".

### 2. Pipeline e Engine (Python)
- **`executable/pipeline.py`**:
  - Atualizados os logs do ciclo de envio para WhatsApp, mudando "Grupos" e "Destinos" para "Canais".
- **`executable/bot_runner.py`**:
  - Ajustado o log de inicialização do robô para imprimir `Canais=` em vez de `Destinos=`.

### 3. Interface de Configuração Local
- **`executable/web/templates/config.html`**:
  - Alterada a label do campo de "Grupos de Destino WhatsApp" para "Canais de Destino WhatsApp".
  - Placeholder atualizado para "Insira os nomes idênticos aos canais".

### 4. Interface do Cliente
- **`client_app/index.html`**:
  - Adicionado o campo "Canais de Destino no WhatsApp (Separados por vírgula)" mapeando para `config.wpp_destinations_str`.
  - Adicionado placeholder "Canal Promo 1, Ofertas 24h".

### 5. Interface de Administração Central
- **`admin/index.html`**:
  - Atualizada a descrição da aba de conexão do WhatsApp para citar "enviar mensagens aos canais".
  - Renomeada a label do campo de configuração de "Destinos WhatsApp" para "Canais de Destino WhatsApp".
  - Alterado o placeholder de "Ex: Canal 1, Grupo 1" para "Ex: Canal Promo 1, Ofertas 24h".

## Razão para Cada Mudança
- **Pedido do cliente**: Retirar o envio para grupos e manter apenas canais, simplificando o fluxo, evitando banimentos desnecessários e focando no modelo de distribuição unidirecional (broadcast/newsletters) que possui maior engajamento.

## Testes Adicionados/Modificados
- Validação estática das expressões regulares e tipos de serialização no Node.js (`isChannel` ou `@newsletter`/`@broadcast`).
- Como a API de WhatsApp é baseada na biblioteca `whatsapp-web.js`, a restrição de `c.isGroup` no filtro garante que grupos não sejam cacheados no servidor, impossibilitando o disparo acidental para os mesmos.

## Impacto na Aplicação
- **Segurança aumentada**: Menor risco de spam e banimentos em grupos públicos/privados.
- **Foco em Canais**: Melhor experiência de entrega direta de cupons e promoções.
- **UI Consistente**: Toda a jornada do usuário no painel central, local e logs agora fala especificamente de "Canais".

## Próximos Passos Recomendados
- Monitorar a fila e logs de envio na primeira hora após a inicialização para certificar-se de que os canais configurados estão recebendo as mensagens corretamente e que nenhum grupo remanescente está sendo importado.
