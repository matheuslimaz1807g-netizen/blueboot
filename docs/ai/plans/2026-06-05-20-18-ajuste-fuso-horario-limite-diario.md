# Plano: Ajuste de Fuso Horário e Limite Diário de Postagens

## Analise da situacao atual

O bot opera em um servidor/VPS configurado no fuso UTC. Atualmente:
1. O `offer_filter.py` calcula o dia atual usando `date.today()` do sistema operacional, que retorna a data baseada no fuso UTC do servidor.
2. O `bot_runner.py` gerencia o `DailyStats` usando `datetime.now(timezone.utc).date()`.
3. Isso causa uma quebra na percepção de limite diário para o usuário no Brasil (UTC-3), já que a data civil no servidor muda às 21h (horário de Brasília). Mensagens enviadas entre 21h e 23h59 de um dia contam na cota do dia seguinte.
4. O limite diário de postagens padrão atual é 10.

## Problemas identificados

1. **Inconsistência de fuso horário:** Mensagens enviadas no final de um dia (a partir das 21:00h de Brasília) consomem o limite do dia seguinte.
2. **Limite diário de 10 postagens:** O usuário deseja aumentar este limite padrão para 15 posts/dia.

## Solucao proposta

1. **Configuração de Timezone (UTC-3):**
   - Utilizar o fuso de Brasília `timezone(timedelta(hours=-3))` para todas as computações que envolvam "dia civil" (`day`) e contadores diários.
   - Ajustar o helper de obter data de hoje no `offer_filter.py` para usar esse fuso horário.
   - Ajustar a classe `DailyStats` no `bot_runner.py` para também usar esse fuso horário (`_TZ_BR`).
2. **Aumentar o limite diário:**
   - Atualizar a chave `"max_posts_per_day"` no `DEFAULT_CONFIG` do `offer_filter.py` de 10 para 15.
3. **Exceção para Ofertas Imperdíveis (Bypass de Limites):**
   - Permitir que ofertas qualificadas como "imperdíveis" (score maior ou igual a 70, que equivale à faixa "Postar imediatamente" da escala de negócios) ignorem os limites diários de postagens e limites de categoria.
   - Adicionar a configuração `"min_score_bypass_limit": 70` ao `DEFAULT_CONFIG`.
   - Modificar a validação em `_evaluate_rules()` para aplicar os limites somente se a oferta possuir score abaixo desse valor limiar.

## Alternativas avaliadas

- **Usar biblioteca pytz/zoneinfo:**
  - *Prós:* Respeita o horário de verão automaticamente.
  - *Contras:* Traz dependências extras ou pode apresentar comportamentos inconsistentes em sistemas sem a base de dados tzdata atualizada.
- **Usar deslocamento fixo (timedelta(hours=-3)):**
  - *Prós:* Simples, extremamente leve, robusto e compatível, sem nenhuma nova dependência. Já é o padrão adotado no resto do projeto (`bot_runner.py`).
  - *Decisão:* Usar deslocamento fixo (UTC-3).

## Cronograma de implementacao

1. **Backup:** Criar ponto de backup seguro com `git stash`.
2. **Testes Unitários:** Adicionar testes que validem que o `offer_filter.py` obtém a data no fuso correto (e de forma consistente).
3. **Implementação no `offer_filter.py`:** Mudar o limite diário padrão para 15 e ajustar todas as queries e logs para usar o dia correspondente ao fuso de Brasília.
4. **Implementação no `bot_runner.py`:** Mudar a lógica de reset do `DailyStats` para coincidir com o mesmo fuso de Brasília.
5. **Validação:** Rodar os testes automatizados e verificar compatibilidade.
6. **Documentação:** Registrar as alterações em `docs/ai/changes/`.

## Riscos e mitigacoes

- *Risco:* Inconsistência entre contadores antigos gravados no banco em UTC e a nova lógica em UTC-3 no dia da transição.
- *Mitigação:* Apenas a transição do dia em que a alteração for feita poderá ter uma contagem ligeiramente deslocada, mas o comportamento se normaliza e estabiliza imediatamente.

## Criterios de sucesso

- O limite diário padrão passa a ser 15.
- O reset de posts diários e os contadores do dashboard viram exatamente à meia-noite do horário de Brasília (UTC-3).
- Todos os testes unitários continuam passando com sucesso.
