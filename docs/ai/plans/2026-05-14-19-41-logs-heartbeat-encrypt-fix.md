# Plano: Logs via Heartbeat + Fix encrypt_field

**Data**: 2026-05-14 19:41

## Problemas

1. **Logs não aparecem no painel do cliente** — bot não envia logs ao servidor
2. **encrypt_field error** — erro ao salvar config no painel do cliente
3. **Deduplicação** — evitar logs repetidos no banco

## Solução

### 1. Logs via Heartbeat
- Adicionar campo `logs` ao schema `LicenseHeartbeatRequest`
- No `license_service.record_heartbeat()`, persistir logs na tabela `log_entries`
- No bot `license.py`, coletar logs pendentes e enviar no payload do heartbeat
- No `main.py`, expor logs pendentes via callback

### 2. Deduplicação
- Manter `_last_sent_index` no bot para rastrear último log enviado
- Enviar apenas novos logs a cada heartbeat (máximo 50 por ciclo)
- Na API, inserir em batch sem verificação de duplicidade (timestamp + license_id são suficientes)

### 3. Fix encrypt_field
- O erro pode ocorrer se Fernet não inicializar corretamente
- Tornar o import explícito e robusto
- Garantir que `config_service.py` funcione mesmo sem credenciais criptografáveis

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `api/app/schemas/schemas.py` | Campo `logs` no HeartbeatRequest |
| `api/app/services/license_service.py` | Persistir logs do heartbeat |
| `api/app/routers/license.py` | Passar logs ao service |
| `executable/license.py` | Enviar logs no heartbeat |
| `executable/main.py` | Callback de logs pendentes |
| `api/app/services/config_service.py` | Fix import encrypt_field |
