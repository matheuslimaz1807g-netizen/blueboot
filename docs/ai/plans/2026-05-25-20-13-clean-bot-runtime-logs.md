# Plano: limpeza de logs operacionais do bot

## Analise da situacao atual

- O container do bot recebe healthcheck em `GET /health`, mas o Flask local nao possui essa rota, gerando `404` repetido.
- O servidor Flask/Werkzeug imprime cada request no stdout, poluindo os logs do Docker.
- `config_loader.merge_configs()` imprime `Config Mesclada` em toda consulta do watcher, mesmo sem mudanca.
- `BotRunner` emite heartbeat informativo a cada minuto.
- `sync_env_vars()` loga tamanho de `ML_COOKIES` sempre que sincroniza, mesmo quando o valor nao mudou.

## Problemas identificados

1. [Alto] `GET /health 404` repetido.
   - Impacto: logs inutilizaveis e falsa impressao de erro.
   - Esforco: baixo.

2. [Alto] Logs de access do Flask/Werkzeug aparecem em toda requisicao.
   - Impacto: ruido continuo em Docker logs.
   - Esforco: baixo.

3. [Medio] `Config Mesclada` aparece a cada watcher.
   - Impacto: ruido a cada 30 segundos.
   - Esforco: baixo.

4. [Medio] Heartbeat operacional repetitivo.
   - Impacto: polui logs sem indicar evento novo.
   - Esforco: baixo.

5. [Medio] Sincronizacao de `ML_COOKIES` loga em toda aplicacao remota.
   - Impacto: ruido e exposicao indireta de metadado sensivel.
   - Esforco: baixo.

## Solucao proposta

- Adicionar rota Flask `/health` retornando JSON simples.
- Desabilitar logger `werkzeug` no executavel.
- Tornar logs de `ConfigLoader` opt-in via env `BLUEBOT_VERBOSE_CONFIG=true`.
- Remover heartbeat repetitivo do `BotRunner`, mantendo apenas eventos reais.
- Logar sincronizacao de env somente quando houver mudanca real, sem tamanho de cookie.

## Cronograma

1. Criar backup via `git stash push`.
2. Adicionar/ajustar testes estaticos para garantir ausencia do ruido.
3. Implementar ajustes em `executable/main.py`, `executable/config_loader.py` e `executable/bot_runner.py`.
4. Validar sintaxe Python e testes possiveis.
5. Registrar changelog.

## Riscos e mitigacao

- Risco: perder informacao util de diagnostico.
  - Mitigacao: manter logs de eventos reais, erro e mudanca de configuracao; deixar config verbose opt-in.

- Risco: healthcheck passar sem validar dependencias externas.
  - Mitigacao: `/health` local valida apenas processo Flask vivo, que e o objetivo do healthcheck do container bot.

## Criterios de sucesso

- `/health` nao gera 404.
- Docker logs nao mostram access log do Werkzeug.
- `Config Mesclada` nao aparece por padrao.
- Heartbeat repetitivo nao aparece por padrao.
- `ML_COOKIES sincronizado: XXXX caracteres` nao aparece.
