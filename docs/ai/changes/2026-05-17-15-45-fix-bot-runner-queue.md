# Modificações Realizadas: Correção da Fila do BotRunner

## Mudanças Realizadas
1. **Atualização do Timeout (`executable/pipeline.py`)**: O timeout do `httpx.AsyncClient` foi aumentado de 20 para 300 segundos. Isso previne que a fila retorne falso prematuramente quando a API nodejs demora devido ao envio encadeado (delay de 1.5s/grupo).
2. **Uso da Variavel de Configuração Correta (`executable/bot_runner.py`)**: Removido o uso do intervalo hardcoded de 10 minutos e atrelado o preenchimento do timeout com a variável de configuração da Dashboard `self._delay`.
3. **Condição de Disparo do Cooldown (`executable/bot_runner.py`)**: A condição de ativação do RateLimit mudou de `if tg_ok or wp_ok:` para `if _processed:`. Isso garante que, caso o endpoint não responda rapidamente e caia por falha HTTP, ele não fure a fila processando imediatamente a próxima mensagem, preservando o RateLimit independente de erros das APIs de mensageria.

## Razão para a mudança
A falta de ativação da variável configurada aliada à baixa duração do timeout do HTTPx do Python fez com que o bot enfileirasse requisições de forma simultânea pro WhatsApp quando o limite de 20 segundos estourava (TimeoutException), criando o cenário de "uma mensagem sendo mandada depois da outra sem nenhum intervalo".

## Impacto na aplicação
O envio pela fila se torna completamente estável e alinhado aos limites de RateLimit selecionados pelo dono da aplicação. O WhatsApp agora terá tempo hábil para entregar mensagens a dezenas de grupos antes de devolver os callbacks.

## Próximos passos recomendados
Pode-se, no futuro, migrar o processo de envio múltiplo no `server.ts` para segundo-plano (não-bloqueante à requisição POST HTTP), liberando o Python mais cedo com status 200 OK e uma Promise de background no Node.js. Por hora, a alteração cobre a estabilidade primária perfeitamente.
