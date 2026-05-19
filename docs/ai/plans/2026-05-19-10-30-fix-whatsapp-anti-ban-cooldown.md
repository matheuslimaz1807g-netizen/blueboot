# Plano: Correção da Fila do WhatsApp e Enforço de Cooldown Global

## Situação Atual
O usuário relatou que a fila anti-ban do WhatsApp está enviando mensagens em sequência muito rápida (ex: um produto às 10:19 e outro às 10:23), ignorando o intervalo configurado (de 15 minutos). 

## Problemas Identificados
1. **Ausência de Estado de Disparo Anterior**: No código atual do `server.ts`, a verificação de delay `setTimeout` é feita de forma sequencial *apenas* se existirem múltiplos itens já presentes na fila no mesmo momento.
2. **Ignorado se a Fila Esvazia**: Se uma mensagem chega quando a fila está vazia, o worker a processa imediatamente e define `isProcessing = false`. Se outra mensagem chega 4 minutos depois, a fila está vazia de novo, o processamento inicia na hora e a envia imediatamente. Ou seja, o cooldown de 15 minutos é ignorado para mensagens que chegam espaçadas!

## Soluções Propostas
- **Introduzir Cooldown Global Persistente (`lastDispatchTime`)**:
  - Armazenar um timestamp global `lastDispatchTime` que registra o momento em que o último disparo bem-sucedido foi realizado no WhatsApp.
  - Ao processar qualquer mensagem da fila, checar se a diferença de tempo desde o `lastDispatchTime` é menor que o `SEND_DELAY` (15 minutos).
  - Se for menor, aguardar o tempo restante antes de fazer o envio de fato.

### Prós:
- Garante de forma absoluta que nunca haverá dois envios no WhatsApp com intervalo menor que o configurado (ex: 15 minutos), protegendo a conta contra banimentos.
- Extremamente simples de implementar e extremamente seguro.

### Contras:
- Nenhum.

## Cronograma de Implementação
1. Criar o plano de ação.
2. Efetuar o backup via `git stash`.
3. Alterar a lógica do `processQueue` no arquivo `Whatsapp/server.ts`.
4. Compilar o Typescript para gerar o `Whatsapp/server.js` atualizado.
5. Commit e push para o repositório remoto.
6. Documentar as mudanças.

## Riscos Potenciais e Mitigação
- Nenhum risco técnico identificado.

## Critérios de Sucesso
- Duas mensagens enviadas espaçadas por menos de 15 minutos devem respeitar o cooldown global e aguardar o tempo restante antes de serem disparadas.
