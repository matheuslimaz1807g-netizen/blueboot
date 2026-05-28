# Plano: Filtro inteligente de ofertas

## Analise da situacao atual

O BlueBot monitora canais do Telegram via `executable/bot_runner.py`, enfileira mensagens com rate limit e processa cada item em `executable/pipeline.py`. O pipeline atual converte links de afiliado, limpa o texto, envia a promocao para API web e publica em Telegram/WhatsApp. Ja existe deduplicacao em memoria por fingerprint no `BotRunner`, mas ela nao guarda historico apos reinicio e nao classifica qualidade da oferta.

Ha alteracoes locais preexistentes em `executable/config_loader.py`, `executable/pipeline.py` e `executable/affiliates/amazon.py`, relacionadas a Amazon. Elas devem ser preservadas.

## Problemas identificados

1. Alto volume de entrada: ler cerca de 900 produtos de outro canal tende a gerar excesso de posts e baixa percepcao de curadoria.
2. Ausencia de pontuacao: o bot nao diferencia oferta forte de oferta fraca.
3. Limites simples: ha rate limit de envio, mas nao limite diario inteligente por categoria.
4. Persistencia limitada: deduplicacao e contadores nao sobrevivem reinicio do processo.
5. Observabilidade limitada: hoje nao ha registro estruturado de por que uma oferta foi aprovada/rejeitada.

## Solucao proposta

Criar `executable/offer_filter.py` com:

- parser de preco, desconto, cupom, frete gratis, Pix, parcelamento, marca e categoria;
- score de 0 a 100;
- regras de rejeicao configuraveis;
- deduplicacao persistente por fingerprint;
- armazenamento local SQLite em `data/offer_filter.sqlite3`;
- API simples `should_post(raw_text, config=None)` para integrar ao pipeline;
- `daily_status(config=None)` para diagnostico futuro.

Integrar no `pipeline.py` logo apos normalizar texto e antes de expandir/converter URLs. Isso economiza processamento quando a oferta claramente nao deve ser publicada. Por compatibilidade operacional, o filtro ficara ativado por padrao no ambiente local via `OFFER_FILTER_ENABLED=true`, mas podera ser desligado com `OFFER_FILTER_ENABLED=false` ou por configuracao remota em `offer_filter.enabled`.

## Alternativas avaliadas

### JSON local

Pros: simples, parecido com o codigo sugerido.
Contras: pior para historico, concorrencia, auditoria e consultas por dia/categoria.

### PostgreSQL da API

Pros: centralizado e consultavel pelo painel.
Contras: acopla o executavel ao backend, exige migracoes, schemas e UI antes de validar o filtro.

### SQLite local

Pros: zero dependencia nova, persistente, auditavel, bom para volume atual e facil de migrar depois.
Contras: historico fica local ate existir sincronizacao com API.

Decisao: SQLite local, com modulo isolado para permitir migracao futura ao PostgreSQL.

## Cronograma de implementacao

1. Adicionar testes unitarios do filtro cobrindo aprovacao, rejeicao por limite, preco, desconto, score, deduplicacao e status diario.
2. Implementar `offer_filter.py` com SQLite e config mesclavel.
3. Integrar `pipeline.py` preservando alteracoes de Amazon existentes.
4. Adicionar variaveis `OFFER_FILTER_*` em `config_loader.py`.
5. Executar testes focados e validacao estatica.
6. Documentar mudancas em `docs/ai/changes`.

## Riscos e mitigacoes

- Risco: bloquear ofertas boas por score agressivo.
  Mitigacao: limites configuraveis por ambiente e logs com motivo de rejeicao.
- Risco: alterar comportamento de clientes existentes.
  Mitigacao: chave `OFFER_FILTER_ENABLED` e configuracao `offer_filter.enabled`.
- Risco: banco local crescer demais.
  Mitigacao: salvar apenas metadados compactos e manter indices por data/fingerprint.
- Risco: parser de preco interpretar textos imperfeitos.
  Mitigacao: testes unitarios e regras conservadoras quando nao houver preco original.

## Criterios de sucesso

- O bot rejeita ofertas duplicadas e fracas antes de converter/enviar.
- Aprovacoes e rejeicoes ficam registradas no SQLite local.
- Limites diarios total e por categoria funcionam mesmo apos reinicio.
- Testes automatizados do filtro passam.
- Alteracoes locais preexistentes sao preservadas.
