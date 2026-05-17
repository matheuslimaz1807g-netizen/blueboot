# Plano: limitar envio WhatsApp/Telegram a cada 10 minutos

## Analise da situacao atual

- `executable/bot_runner.py` faz polling das fontes Telegram a cada 10 segundos.
- Ao encontrar mensagens novas, o codigo chama `asyncio.create_task(self._process_and_count(message))` para cada mensagem.
- `executable/pipeline.py` processa a mensagem e envia imediatamente para Telegram e WhatsApp.
- Com varias mensagens/produtos novos, o bot dispara varias tarefas em paralelo, gerando envios em sequencia rapida.

## Problema identificado

- Critico: o bot nao respeita intervalo minimo entre disparos para WhatsApp/Telegram.
- Impacto: alto risco de bloqueio do WhatsApp por comportamento de spam e excesso de mensagens em pouco tempo.

## Solucao proposta

- Criar uma fila assíncrona interna no `BotRunner`.
- O polling continua lendo mensagens novas para nao perder produtos, mas apenas coloca na fila.
- Um worker unico consome a fila em ordem e chama `processar_mensagem`.
- Apos cada tentativa de envio/processamento, o worker aguarda 600 segundos antes de processar o proximo item.
- Expor tamanho da fila e proximo disparo nos stats para facilitar diagnostico local.

## Pros e contras

- Pros: evita spam, preserva produtos em fila, centraliza regra no orquestrador e nao altera a pipeline de conversao/envio.
- Contras: se chegarem muitos produtos, a fila pode crescer e alguns envios ficarao atrasados; isso e intencional para proteger a conta.

## Cronograma de implementacao

1. Registrar plano e backup.
2. Alterar `BotRunner` para usar fila de envio sequencial com intervalo de 10 minutos.
3. Adicionar testes estaticos para proteger a regra de 600 segundos e remover o envio paralelo.
4. Validar sintaxe Python quando possivel e documentar mudancas.

## Riscos e mitigacao

- Risco: perder mensagens se o cursor avancar antes do envio.
  - Mitigacao: a mensagem fica em fila em memoria antes do cursor ser avancado.
- Risco: fila em memoria ser perdida em restart.
  - Mitigacao: comportamento atual tambem nao tem persistencia local de fila; documentar como risco residual.
- Risco: bloquear todo o polling durante o intervalo.
  - Mitigacao: polling e worker ficam separados; o polling segue coletando mensagens.

## Criterios de sucesso

- Nao existe mais `asyncio.create_task(self._process_and_count(message))` para disparar envios paralelos.
- Existe intervalo minimo de 600 segundos entre processamentos da fila.
- Produtos novos sao enfileirados e processados em ordem.
- Testes estaticos protegem a regra principal.
