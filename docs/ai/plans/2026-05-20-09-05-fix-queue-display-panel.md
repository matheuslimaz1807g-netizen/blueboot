# Fix: Queue Items Not Displaying in Client Panel

## Problema
O bot enfileira mensagens e mostra cooldown nos logs, mas o painel do cliente sempre mostra "Nenhum item aguardando na fila".

## Causa Raiz
1. `get_queue_items()` acessa `asyncio.Queue._queue` de outra thread (heartbeat thread) - unsafe
2. A leitura de `_active_delivery_item` pode ter race condition com a thread do asyncio loop

## Solução
Manter um snapshot thread-safe dos itens da fila usando `self._lock`, atualizado pelo delivery worker sempre que o estado muda. O heartbeat lê apenas o snapshot.

## Arquivos Alterados
- `executable/bot_runner.py` - Thread-safe queue snapshot
