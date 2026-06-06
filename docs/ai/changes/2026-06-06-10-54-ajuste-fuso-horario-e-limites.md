# Mudanças: Ajuste de Fuso Horário e Limite Diário de Postagens

## Mudanças realizadas

- Adicionado o fuso horário de Brasília (UTC-3) representado por `timezone(timedelta(hours=-3))` no arquivo `executable/offer_filter.py`.
- Criado o helper `_get_today_br() -> str` no `executable/offer_filter.py` para determinar a data no formato `"YYYY-MM-DD"` com base no fuso de Brasília.
- Atualizado o campo `timestamp` padrão de instâncias da classe `Offer` para usar o fuso brasileiro (`datetime.now(TZ_BR).isoformat()`).
- Substituído o uso de `str(date.today())` por `_get_today_br()` em consultas do SQLite e rotinas de salvamento no `executable/offer_filter.py`.
- Alterado o limite diário padrão `"max_posts_per_day"` de 10 para 15 no `DEFAULT_CONFIG` do `executable/offer_filter.py`.
- Adicionado o parâmetro `"min_score_bypass_limit": 70` no `DEFAULT_CONFIG` do `executable/offer_filter.py`.
- Implementada a lógica de bypass de limites (`bypass_limit`) em `_evaluate_rules()` de `executable/offer_filter.py` para ofertas com score maior ou igual a 70 (ofertas classificadas na categoria "Postar imediatamente").
- Atualizado a classe `DailyStats` no `executable/bot_runner.py` para calcular e resetar o dia civil (`day`) utilizando a constante `_TZ_BR` (UTC-3) em vez de `timezone.utc`.
- Corrigido o teste unitário `test_should_post_rejects_low_discount_when_original_price_exists` que estava quebrado devido à identificação de marca e bônus de score no texto mocado.
- Adicionados os testes `test_should_post_uses_brazil_timezone` e `test_should_post_bypasses_daily_limit_for_premium_offers` em `api/tests/test_offer_filter.py`.

## Razão das mudanças

- O bot estava rodando em servidores VPS operando em fuso UTC. Como consequência, o limite diário e os contadores do dashboard eram redefinidos às 21:00h do horário de Brasília (UTC-3). Posts enviados no final da noite eram computados indevidamente na cota do dia seguinte.
- O limite de postagens diárias precisava ser aumentado de 10 para 15 a pedido do usuário.
- Havia a necessidade de abrir exceção automática aos limites (geral e por categoria) caso surgisse uma promoção imperdível (score elevado >= 70).

## Testes adicionados/modificados

- `test_should_post_rejects_low_discount_when_original_price_exists` (corrigido)
- `test_should_post_uses_brazil_timezone` (novo)
- `test_should_post_bypasses_daily_limit_for_premium_offers` (novo)

## Validação executada

- Executado o `pytest` focando no arquivo do filtro: `python -m pytest api/tests/test_offer_filter.py`.
- Todos os 7 testes passaram com sucesso absoluta.

## Impacto na aplicação

- O limite diário de postagens padrão do bot agora é **15**.
- O reset do limite de posts do dia e a contagem de mensagens do painel VPS agora viram exatamente à meia-noite (00:00h) do horário de Brasília.
- Ofertas consideradas altamente atrativas/imperdíveis (score >= 70) serão enviadas imediatamente, ignorando os limites diário e de categoria.

## Próximos passos recomendados

- Monitorar se o número de bypasses por score alto não gera uma quantidade excessiva de envios, ajustando o parâmetro `min_score_bypass_limit` se necessário.
