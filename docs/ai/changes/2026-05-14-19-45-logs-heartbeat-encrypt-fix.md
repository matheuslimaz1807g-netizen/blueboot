# Mudanças: Logs via Heartbeat + Fix encrypt_field

**Data**: 2026-05-14 19:45
**Tipo**: Feature + Bugfix

## Mudanças Realizadas

### 1. Logs no Painel do Cliente (Feature)

**Problema**: O painel `app.bluebotapp.com.br` mostrava apenas 1 log ("Máquina vinculada") porque o bot nunca enviava logs ao servidor.

**Solução**: Os logs agora são enviados via heartbeat (a cada 15s).

**Fluxo novo:**
```
Bot → add_log() → deque em memória
     ↓ (a cada 15s)
Heartbeat → payload + logs pendentes → POST /license/heartbeat
     ↓
API → persiste na tabela log_entries
     ↓
Painel Cliente → GET /client/logs → exibe logs reais
```

**Arquivos alterados:**

| Arquivo | Mudança |
|---------|---------|
| `api/app/schemas/schemas.py` | `HeartbeatLogItem` schema + campo `logs` no `LicenseHeartbeatRequest` |
| `api/app/services/license_service.py` | `record_heartbeat()` persiste logs + pruning (max 500/licença) |
| `api/app/routers/license.py` | Passa `body.logs` ao service |
| `executable/license.py` | `logs_callback` no heartbeat worker |
| `executable/main.py` | `get_pending_logs_callback()` com deduplicação por índice |

**Deduplicação:**
- `_last_sent_log_index` rastreia o último log enviado
- Apenas logs novos são incluídos no heartbeat (máx 50/ciclo)
- Se a deque for resetada, o índice é reajustado automaticamente

**Retenção:**
- Máximo 500 logs por licença no banco
- Logs mais antigos são deletados automaticamente via pruning

### 2. Fix encrypt_field (Bugfix)

**Problema**: `cannot access local variable 'encrypt_field' where it is not associated with a value`

**Causa**: Possível shadowing de variável pelo Python (o nome `encrypt_field` sendo detectado como variável local em algum escopo)

**Solução**: Imports renomeados com alias:
```python
from app.core.security import decrypt_field as _decrypt, encrypt_field as _encrypt
```

**Arquivo**: `api/app/services/config_service.py`

## Deploy na VPS

```bash
cd /opt/bluebot
git pull

# Rebuild API (novo schema/service)
docker compose build api
docker compose up -d api

# Rebuild bot (novo heartbeat com logs)
cd clientes/matheus
docker compose build bot_matheus
docker compose up -d bot_matheus
```

## Validação

1. Acessar `app.bluebotapp.com.br` → logs devem começar a aparecer em ~15s
2. Alterar configurações no painel → deve salvar sem erro
3. `docker compose logs -f bot_matheus` → confirmar que heartbeat envia logs
