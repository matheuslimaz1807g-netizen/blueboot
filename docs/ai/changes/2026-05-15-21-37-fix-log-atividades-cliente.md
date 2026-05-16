# Mudancas: log de atividades do painel do cliente

## Mudancas realizadas

- Corrigido `client_app/index.html` para exibir estado vazio em "Logs de Atividade".
- `loadLogs()` agora aceita todos os niveis suportados pelo bot/API: `success`, `error`, `info` e `warning`.
- Adicionado guard contra respostas nao-array de `/client/logs`, evitando quebra do painel em erros temporarios da API.
- Adicionados helpers ausentes no Alpine:
  - `fmtDate`
  - `fmtRelative`
  - `formatLevel`
  - `logLevelClass`
- Adicionado teste estatico em `api/tests/test_client_app_static.py` para proteger a sintaxe do script e os requisitos do log de atividades.
- Corrigido `executable/main.py` para enviar logs ao heartbeat por uma fila dedicada `_pending_remote_logs`, em vez de usar indice sobre `_logs`.
- Adicionado teste estatico em `api/tests/test_executable_log_forwarding_static.py` para proteger a fila de logs pendentes.

## Razao para cada mudanca

- O log de execucao informado mostra que o bot gera eventos `SUCCESS` localmente.
- O fluxo correto e: bot local -> heartbeat `/license/heartbeat` -> tabela `log_entries` -> painel via `/client/logs`.
- O `Whatsapp/server.ts` nao persiste logs; ele apenas executa `/status` e `/send`.
- O painel tinha risco de falha de renderizacao porque chamava `fmtDate` e `fmtRelative` sem definir essas funcoes.
- O filtro anterior ocultava `info` e `warning`, reduzindo muito a visibilidade do log de atividades.
- O controle anterior por `_last_sent_log_index` podia travar quando `_logs` atingia `maxlen=300`, porque o tamanho do deque parava de crescer mesmo com logs novos entrando.

## Testes adicionados/modificados

- `api/tests/test_client_app_static.py`
  - Valida sintaxe JavaScript do script do painel do cliente quando `node` estiver disponivel.
  - Garante existencia dos helpers e da lista completa de niveis suportados.
- `api/tests/test_executable_log_forwarding_static.py`
  - Garante que o executavel usa fila pendente para heartbeat e nao usa mais `_last_sent_log_index`.

## Validacao executada

- Backup: `git stash push -m "BACKUP-2026-05-15-21-37: diagnostico-log-atividades-cliente"` retornou `No local changes to save`.
- Validacao com Node via runtime MCP:
  - Sintaxe JavaScript: `ok`.
  - Checks estaticos: `fmtDate`, `fmtRelative`, `Array.isArray`, niveis suportados e estado vazio presentes.
- `python -m py_compile executable/main.py api/tests/test_client_app_static.py api/tests/test_executable_log_forwarding_static.py` executado com sucesso usando o Python empacotado do Codex.

## Limitacoes

- `pytest` nao foi executado porque o ambiente local nao possui `pytest` instalado e o launcher `py` aponta para uma instalacao sem permissao de execucao.

## Impacto na aplicacao

- O painel do cliente deixa de quebrar por helpers inexistentes.
- Logs informativos e avisos passam a aparecer quando retornados pela API.
- Logs novos continuam sendo enviados ao heartbeat mesmo depois de o buffer local `_logs` atingir 300 itens.
- Se a tela continuar vazia em producao, o proximo diagnostico deve verificar se o heartbeat do container esta recebendo HTTP 200 em `/license/heartbeat` e se `/client/logs` retorna registros para a licenca autenticada.

## Proximos passos recomendados

- Fazer deploy do `client_app/index.html` atualizado.
- Fazer deploy/rebuild do executavel/container do bot para aplicar `executable/main.py`.
- No ambiente de producao, confirmar no navegador se `GET https://api.bluebotapp.com.br/client/logs` retorna os registros recentes da licenca.
