# Mudancas: Filtro inteligente de ofertas

## Mudancas realizadas

- Criado `executable/offer_filter.py` com parser, score, regras de rejeicao, deduplicacao e persistencia local em SQLite.
- Integrado o filtro no inicio de `executable/pipeline.py`, antes da expansao/conversao de links.
- Adicionadas configuracoes `OFFER_FILTER_*` em `executable/config_loader.py` e `.env.example`.
- Incluido `offer_filter` nos campos monitorados pelo watcher de configuracao em `executable/main.py`.
- Adicionados testes em `api/tests/test_offer_filter.py`.
- Registrado backup em `docs/ai/backups.md`.

## Razao das mudancas

O canal precisa reduzir volume e aumentar curadoria. O filtro evita publicar ofertas duplicadas, fracas, fora de faixa de preco ou acima dos limites diarios antes de gastar tempo convertendo links e enviando para destinos.

## Testes adicionados/modificados

- `test_should_post_approves_strong_offer_and_persists_status`
- `test_should_post_rejects_duplicate_even_after_new_call`
- `test_should_post_rejects_by_daily_category_limit`
- `test_should_post_rejects_low_discount_when_original_price_exists`
- `test_should_post_can_be_disabled_without_persisting`

## Validacao executada

- `python -m py_compile` nos arquivos Python alterados.
- Mini-runner com Python empacotado reproduzindo os cenarios dos testes, pois `pytest` nao esta instalado no ambiente atual.

## Impacto na aplicacao

- Por padrao, o bot passa a publicar no maximo 10 ofertas por dia, ate 3 por categoria, com score minimo 40.
- Rejeicoes sao registradas localmente em `data/offer_filter.sqlite3`.
- O filtro pode ser desligado com `OFFER_FILTER_ENABLED=false`.
- Mudancas locais existentes de Amazon foram preservadas.

## Proximos passos recomendados

- Expor os parametros do filtro no painel do cliente.
- Criar uma tela de relatorio com aprovadas/rejeitadas e principais motivos.
- Ajustar limites apos observar alguns dias de dados reais do canal.
