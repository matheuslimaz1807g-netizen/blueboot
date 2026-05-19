# Plano de Implementação: Correção de Limite de Delay e Timezone de Envio

Este plano detalha o diagnóstico e a correção para dois problemas críticos no BlueBot:
1. **Fila em sequência (Stuck delay)**: O usuário ajustava o delay no painel admin, mas o bot continuava disparando em sequência. Descobrimos que a API possuía validação estrita no Pydantic (`le=60`), rejeitando qualquer valor superior a 60 segundos com erro HTTP 422, impedindo o salvamento correto das alterações.
2. **Timezone incorreto (Formato de Hora)**: O log mostra o horário da atividade convertido para local no cabeçalho (ex: `10:50:41`), mas o texto interno indica liberação às `13:50:41` (UTC), gerando a falsa impressão de um atraso de 3 horas.

---

## 🛠️ Análise Técnica e Diagnóstico

### 1. Limitação da API para `delay_segundos`
No arquivo `api/app/schemas/schemas.py`:
```python
delay_segundos: int = Field(default=3, ge=1, le=60)
```
Quando o usuário configurava um delay maior (como 5 ou 10 minutos) no painel admin, a API retornava um erro silencioso ou visível de validação (HTTP 422) e a configuração mantinha-se no valor antigo/padrão (3 segundos).

**Solução**:
- Alterar `le=60` para `le=86400` (permitindo até 24 horas).
- Atualizar a interface do cliente local (`executable/web/templates/config.html`) de um slider restrito a 60 segundos para um campo numérico flexível.

### 2. Discrepância de Horários (America/Sao_Paulo)
No arquivo `executable/bot_runner.py`:
```python
next_time_str = datetime.fromtimestamp(next_dispatch).strftime("%H:%M:%S")
```
Como a VPS roda em UTC, `datetime.fromtimestamp()` interpreta e formata o horário em UTC.
No navegador, o log é exibido usando a hora local (UTC-3).

**Solução**:
- Importar `timedelta` em `bot_runner.py`.
- Formatar o horário estimando o fuso de Brasília (`UTC-3`):
```python
tz_br = timezone(timedelta(hours=-3))
next_time_str = datetime.fromtimestamp(next_dispatch, tz=tz_br).strftime("%H:%M:%S")
```

---

## 📅 Cronograma e Critérios de Sucesso

1. **Alteração do Schema da API**: Substituir limite `le=60` por `le=86400`.
2. **Alteração da Interface Local**: Modificar slider para input numérico livre.
3. **Ajuste de Timezone no Bot**: Empregar offset `UTC-3` para formatar strings de previsão de envio.
4. **Validação**: Testar salvamento de delays altos (ex: `600` segundos) e checar os logs.

---

## ⚠️ Riscos e Mitigações

- **Risco**: Impacto em outras instâncias com fusos horários diferentes.
- **Mitigação**: O fuso de Brasília (UTC-3) é o padrão nacional de operação da plataforma.
