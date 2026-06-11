# Correção: Filtro Inteligente de Ofertas — `offer_filter_enabled`

**Data:** 2026-06-11 12:47  
**Autor:** Agente IA  
**Arquivos modificados:** `client_app/index.html`, `executable/pipeline.py`

---

## Problemas Identificados

### Bug 1 — Checkbox "Filtro Ativo" revertendo ao estado anterior

**Causa raiz:** Duas sub-causas combinadas:

1. **Expressão `!== false` ambígua** (linha 691 do `client_app/index.html`):
   ```js
   // ANTES (problemático)
   offer_filter_enabled: cfg.offer_filter_enabled !== false,
   // Se o valor fosse null/undefined, resultava em true indevido
   
   // DEPOIS (correto)
   offer_filter_enabled: cfg.offer_filter_enabled === true,
   ```

2. **`saveConfig()` não recarregava o estado do servidor** após salvar:
   O poll de 30s (`setInterval → loadAll()`) poderia sobrescrever o valor local com o valor antigo do servidor se houvesse qualquer atraso ou inconsistência. Após salvar, agora fazemos `await this.loadConfig()` para confirmar o estado persistido imediatamente.

### Bug 2 — Log do Filtro Inteligente não aparecia no painel

**Causa raiz:** O `pipeline.py` não tinha `log_callback` explícito para o estado do `offer_filter_enabled`, diferente de `send_whatsapp` e `conv_ali` que logam seu status.

**Correção:** Adicionado log `[Filtro] ENABLED=True/False` antes do `should_post()`, e um log adicional quando o filtro está desativado (para reforçar que todas as ofertas passam).

---

## Mudanças Realizadas

### `client_app/index.html`

1. `loadConfig()` — Linha 691:
   - `bot_enabled: cfg.bot_enabled !== false` → `cfg.bot_enabled === true`
   - `offer_filter_enabled: cfg.offer_filter_enabled !== false` → `cfg.offer_filter_enabled === true`
   
2. `saveConfig()` — Após a chamada PUT:
   - Adicionado `await this.loadConfig()` dentro do bloco de sucesso

### `executable/pipeline.py`

1. `processar_mensagem()` — Bloco offer_filter (linhas 169-190):
   - Refatorada captura do `filter_enabled` em variável local para clareza
   - Adicionado `log_callback("info", f"[{msg_id}] [Filtro] ENABLED={...}")` antes do `should_post()`
   - Adicionado log adicional quando filtro está desativado: `"[Filtro] Filtro Inteligente desativado — todas as ofertas sao publicadas."`

---

## Comportamento Esperado

- **Filtro ATIVO (marcado):** Log: `[Filtro] ENABLED=True`. Ofertas passam pelo filtro de score/desconto.
- **Filtro INATIVO (desmarcado):** Log: `[Filtro] ENABLED=False` + `[Filtro] Filtro Inteligente desativado — todas as ofertas sao publicadas.`
- O checkbox no painel mantém o estado salvo corretamente após salvar e no próximo reload.

---

## Impacto

- Sem breaking changes
- Sem mudanças no banco de dados (migração 013 já estava correta)
- Logs adicionais no painel do cliente
