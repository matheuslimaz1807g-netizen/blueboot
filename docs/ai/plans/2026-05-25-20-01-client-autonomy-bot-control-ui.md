# Plano: autonomia do cliente, controle do bot e ajustes de console

## Analise da situacao atual

- O painel do cliente em `client_app/index.html` ja autentica via `/auth/login/client`, carrega `/client/me`, `/client/config` e `/client/logs`.
- A configuracao remota em `client_configs` ja guarda credenciais criptografadas de Telegram, Shopee, AliExpress e Mercado Livre, mas a UI do cliente expoe apenas destinos, fontes e toggles basicos.
- O endpoint WhatsApp fica em `whatsapp_endpoint` e deve permanecer fora do painel do cliente.
- O bot local ja possui `BotRunner.start()` e `BotRunner.stop()`, mas o controle visual existe apenas no dashboard local do executavel.
- O watcher em `executable/main.py` ja busca configuracao remota a cada 30 segundos e aplica mudancas no bot.
- O console admin em `admin/index.html` possui bug de ordem/quantidade de colunas: a tabela mostra `note` antes da chave, mas os cabecalhos nao acompanham a ordem.
- Os logs do cliente sao filtrados para apenas `success` e `error`, reduzindo visibilidade operacional.

## Problemas identificados

1. [Alto] Cliente nao consegue editar credenciais importantes da propria licenca.
   - Impacto: dependencia do admin para ajustes simples de API ID, tokens e cookies.
   - Esforco: medio.

2. [Alto] Cliente nao consegue iniciar/parar o bot pelo painel SaaS.
   - Impacto: baixa autonomia operacional.
   - Esforco: medio, requer campo persistido e watcher no bot.

3. [Medio] Console admin tem colunas desalinhadas.
   - Impacto: leitura incorreta da tabela e possivel confusao operacional.
   - Esforco: baixo.

4. [Medio] Logs do cliente perdem eventos `info` e `warning`.
   - Impacto: diagnostico mais pobre no painel do cliente.
   - Esforco: baixo.

5. [Medio] UI/UX do painel cliente concentra configuracoes em uma lista curta e pouco organizada.
   - Impacto: clientes nao encontram facilmente as areas de Telegram, afiliados, destinos e controle do bot.
   - Esforco: medio.

## Solucoes propostas

### Opcao escolhida: `bot_enabled` na configuracao remota

Adicionar um booleano `bot_enabled` em `client_configs`, expor em `ConfigIn/ConfigOut`, permitir que o cliente altere esse campo e fazer o watcher do executavel iniciar/parar o `BotRunner` conforme o valor.

Pros:
- Usa o canal remoto ja existente.
- Nao depende de expor o dashboard local do bot nem o endpoint WhatsApp.
- Fica persistente e auditavel na configuracao da licenca.
- Mantem isolamento por licenca.

Contras:
- O start/stop nao e instantaneo; segue o ciclo do watcher, hoje em ate 30 segundos.
- Requer migration Alembic e ajuste de testes.

### Alternativa descartada: endpoint de comando separado

Criar uma tabela/rota de comandos e fazer o bot buscar comandos no heartbeat.

Pros:
- Poderia ter semantica de comando mais explicita.

Contras:
- Maior superficie de mudanca.
- Heartbeat atual nao processa retorno do servidor.
- Exige mais persistencia e estados intermediarios.

## Cronograma de implementacao

1. Criar backup obrigatório com `git stash push`.
2. Adicionar testes estaticos para:
   - Painel cliente expor campos de credenciais e controle Start/Stop.
   - Admin ter cabecalhos alinhados com colunas.
   - Bot watcher reconhecer `bot_enabled`.
3. Implementar backend:
   - Modelo `ClientConfig.bot_enabled`.
   - Schema `ConfigIn/ConfigOut`.
   - Service `config_service`.
   - Migration Alembic.
4. Implementar bot:
   - Respeitar `bot_enabled` no start inicial.
   - Watcher iniciar/parar quando `bot_enabled` mudar.
   - Logs de start/stop remoto.
5. Implementar UI:
   - Painel cliente com controle do bot.
   - Secoes de Telegram, afiliados, destinos e envio.
   - Manter `whatsapp_endpoint` fora da UI do cliente.
   - Melhorar logs exibindo todos os niveis suportados.
   - Corrigir ordem/colspan da tabela admin.
6. Validar com testes e checagem de sintaxe JavaScript.
7. Documentar mudancas em `docs/ai/changes`.

## Riscos e mitigacao

- Risco: `bot_enabled` ausente em bancos antigos.
  - Mitigacao: migration com default `true`, schema com default `true` e retorno tolerante.

- Risco: cliente apagar credenciais sem querer.
  - Mitigacao: manter comportamento atual de envio explicito; campos vazios limpam, valores existentes voltam descriptografados como ja ocorre hoje.

- Risco: start remoto sem API ID/API Hash validos.
  - Mitigacao: watcher so chama `start()` quando credenciais basicas existem; caso contrario registra log de erro/aviso.

- Risco: endpoint WhatsApp aparecer para cliente.
  - Mitigacao: nao criar input para `whatsapp_endpoint` no painel cliente e remover o campo do payload do cliente antes de salvar.

## Criterios de sucesso

- Cliente consegue editar API ID, API Hash, telefone, fontes, destino Telegram, destinos WhatsApp, tokens/cookies de afiliados e toggles.
- Cliente nao consegue editar `whatsapp_endpoint` pela UI.
- Cliente consegue solicitar Start/Stop do bot pelo painel.
- Bot aplica Start/Stop pelo watcher remoto.
- Console admin exibe cabecalhos e celulas na mesma ordem.
- Logs do cliente mostram niveis `info`, `success`, `warning` e `error` quando recebidos.
- Testes automatizados relevantes passam.

## Backup planejado

- Metodo: `git stash push -m "BACKUP-2026-05-25-20-01: client autonomy bot control ui"`
- Registro: atualizar `docs/ai/backups.md` apos executar.
