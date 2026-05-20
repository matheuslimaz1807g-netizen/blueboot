# Fix: Fila de Envio Não Aparece no Painel do Cliente

**Data**: 2026-05-20 09:05 (BRT)

## Problema
O bot enfileirava mensagens e exibia cooldown nos logs do container, mas o painel do cliente (`client_app`) sempre mostrava "Nenhum item aguardando na fila".

## Causa Raiz
1. **Acesso cross-thread inseguro**: `get_queue_items()` era chamado pela thread do heartbeat mas acessava `asyncio.Queue._queue` (internal deque) que pertence ao asyncio event loop em outra thread.
2. **Snapshot não persistente**: O estado da fila era calculado on-demand, e qualquer exceção silenciosa no acesso cross-thread resultava em lista vazia.
3. **Cooldown bloqueava o refresh**: O worker esperava o cooldown inteiro (`timeout=time_remaining`) sem atualizar o snapshot, então o ETA ficava desatualizado.

## Solução
- **`_queue_snapshot`**: Nova lista `list[dict]` protegida por `_lock`, mantida pelo delivery worker dentro do asyncio loop (thread-safe por design).
- **`_refresh_queue_snapshot()`**: Método que recalcula o snapshot. Chamado em 4 pontos:
  1. Quando um item é enfileirado (`queue.put`)
  2. Quando o worker pega um item da fila (`queue.get`)
  3. Periodicamente durante o cooldown (a cada ≤30s)
  4. Quando o item é finalizado (`finally`)
- **`get_queue_items()`**: Agora apenas retorna uma cópia do snapshot sob `_lock` — zero acesso a internals do asyncio.
- **Cooldown chunked**: O wait do cooldown agora usa `min(time_remaining, 30)` para refresh periódico do snapshot.

## Arquivos Alterados
- `executable/bot_runner.py`

## Impacto
- O painel do cliente agora mostra itens na fila em tempo real
- Performance: snapshot atualizado apenas quando estado muda (não a cada poll)
- Sem breaking changes na API
