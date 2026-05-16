# Plano: corrigir log de atividades do painel do cliente

## Analise da situacao atual

- O painel do cliente (`client_app/index.html`) consome `GET /client/logs`.
- A API (`api/app/routers/client.py`) retorna registros da tabela `log_entries` filtrados pela licenca autenticada.
- Os logs sao gravados pelo heartbeat em `api/app/services/license_service.py`, a partir dos eventos enviados pelo robo em `executable/main.py`.
- O `Whatsapp/server.ts` apenas responde `/status` e `/send`; ele nao persiste logs no painel central.
- O log informado pelo usuario confirma que o bot local gerou eventos `SUCCESS` para Telegram e WhatsApp.

## Problemas identificados

1. O painel do cliente filtra logs e exibe apenas `success` e `error`, ocultando `info` e `warning`.
2. O painel referencia `fmtRelative` e `fmtDate`, mas essas funcoes nao existem no objeto Alpine.
3. A interface nao mostra estado vazio/erro para a lista de logs, o que dificulta diferenciar "sem logs" de falha de renderizacao.
4. O envio remoto dos logs usa um indice sobre `_logs`, que e um `deque(maxlen=300)`. Quando o deque atinge 300 itens, o tamanho para de crescer e o heartbeat pode parar de detectar logs novos.

## Solucoes propostas

### Opcao A: Corrigir apenas o frontend

Pros:
- Baixo risco e baixo impacto.
- Resolve falhas de renderizacao e deixa visiveis os logs ja retornados pela API.
- Nao muda contrato da API nem persistencia.

Contras:
- Se o heartbeat nao estiver chegando em producao, sera necessario diagnostico operacional adicional.

### Opcao B: Alterar backend para transformar logs ou criar endpoint novo

Pros:
- Poderia centralizar regras de exibicao.

Contras:
- Maior impacto sem evidencia de falha no backend.
- Pode esconder a causa real se o problema for apenas visual.

## Abordagem escolhida

Aplicar a Opcao A primeiro: corrigir o painel do cliente para renderizar logs de forma robusta, incluindo `info`, `warning`, `success` e `error`, e adicionar funcoes de data ausentes.

Complemento apos analise do log real: corrigir tambem o produtor dos logs em `executable/main.py`, substituindo o controle por indice por uma fila dedicada de logs pendentes para envio remoto.

## Cronograma de implementacao

1. Criar teste estatico que falha para garantir que o painel possui helpers e nao filtra logs validos.
2. Corrigir `client_app/index.html`.
3. Criar teste estatico para proteger a fila de logs pendentes no executavel.
4. Corrigir `executable/main.py`.
5. Executar testes focados.
6. Documentar mudancas em `docs/ai/changes`.

## Riscos e mitigacao

- Risco: exibir muitos logs informativos.
  - Mitigacao: manter limite da API e deduplicacao existente.
- Risco: formatacao de datas inconsistente.
  - Mitigacao: usar `toLocaleDateString`/`toLocaleString` com fallback para valores invalidos.
- Risco: problema real estar no heartbeat em producao.
  - Mitigacao: usar fila dedicada drenada pelo heartbeat, independente do tamanho do deque usado pelo painel local.

## Criterios de sucesso

- O script do painel do cliente passa em validacao de sintaxe.
- `loadLogs()` nao descarta `info` e `warning`.
- `fmtDate` e `fmtRelative` existem.
- O painel mostra estado vazio quando nao ha logs.
- Logs novos continuam sendo enviados ao heartbeat mesmo apos `_logs` atingir `maxlen`.
- Mudancas documentadas.
