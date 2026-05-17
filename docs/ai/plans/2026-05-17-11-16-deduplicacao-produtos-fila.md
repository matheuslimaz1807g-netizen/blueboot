# Plano: deduplicacao de produtos entre fontes monitoradas

## Analise da situacao atual

- O bot monitora multiplas fontes configuradas em `sources`, por exemplo `t.me/lobaopromo` e `t.me/pobregram`.
- A deduplicacao existente em `BotRunner` usa `(chat_id, msg_id)`, evitando processar a mesma mensagem do mesmo canal duas vezes.
- Essa regra nao detecta o mesmo produto publicado em canais diferentes, pois o `chat_id` e o `msg_id` mudam.
- A fila de rate limit criada para WhatsApp/Telegram ainda pode receber duplicatas se duas fontes publicarem a mesma oferta.

## Problema identificado

- Alto impacto: o mesmo produto pode ser enviado duas vezes, apenas com origem diferente.
- Impacto: aumenta fila, atrasa ofertas unicas e eleva risco de spam/bloqueio no WhatsApp.

## Solucao proposta

- Criar assinatura normalizada de produto antes de enfileirar:
  - normalizar texto;
  - remover URLs e hashtags;
  - extrair titulo provavel e preco;
  - usar URLs como fallback quando nao houver texto suficiente.
- Manter duas estruturas:
  - produtos pendentes na fila;
  - produtos recentes por TTL.
- Se a assinatura ja estiver pendente ou recente, ignorar a mensagem duplicada antes de entrar na fila.
- Liberar assinatura pendente quando o worker concluir o processamento.

## Pros e contras

- Pros: impede duplicidade entre fontes, reduz spam, preserva produtos unicos e nao depende da API do WhatsApp.
- Contras: assinaturas por texto podem ter falso positivo se duas ofertas tiverem titulo/preco muito parecidos; mitigado usando titulo + preco + fallback de URL.

## Cronograma de implementacao

1. Registrar plano.
2. Adicionar geracao de assinatura e memoria de deduplicacao no `BotRunner`.
3. Aplicar dedupe antes de `delivery_queue.put`.
4. Atualizar testes estaticos.
5. Validar sintaxe e contratos.

## Riscos e mitigacao

- Risco: produto igual com texto levemente diferente passar.
  - Mitigacao: normalizacao remove URLs, pontuacao e ruido comum, mas preserva titulo/preco.
- Risco: produto diferente com mesmo titulo e preco ser ignorado.
  - Mitigacao: TTL limitado e assinatura com texto significativo.

## Criterios de sucesso

- Mensagens duplicadas entre fontes nao entram duas vezes na fila.
- Existe teste protegendo `_product_fingerprint`, `_remember_product` e liberacao de pendentes.
- Sintaxe Python continua valida.
