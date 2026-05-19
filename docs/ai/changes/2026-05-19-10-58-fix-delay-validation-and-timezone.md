# Registro de Mudanças: Correção de Validação de Delay e Ajuste de Timezone nos Logs

Este documento registra as alterações realizadas para corrigir o limite de delay da API e resolver a divergência de timezone exibida nos logs do cliente.

---

## 📝 Mudanças Realizadas

### 1. API: Flexibilização da validação do Delay
**Arquivo**: `api/app/schemas/schemas.py`
- Alterada a restrição do campo `delay_segundos` de `le=60` (limite máximo de 60 segundos) para `le=86400` (limite de 24 horas). Isso permite que o painel admin salve delays maiores (como 3 minutos, 10 minutos, 15 minutos) com sucesso.

### 2. Interface Local: Input de número flexível
**Arquivo**: `executable/web/templates/config.html`
- Substituído o controle `<input type="range">` por um `<input type="number">` limpo e profissional, permitindo ao usuário digitar livremente o delay desejado em segundos (ex: 600 para 10 minutos).
- Ajustado o script JS de carregamento das configurações para atualizar opcionalmente a legenda de exibição, evitando erros em elementos HTML ausentes.

### 3. Robô (Python): Correção do Timezone do log interno
**Arquivo**: `executable/bot_runner.py`
- Importado `timedelta` do módulo `datetime`.
- Substituída a chamada `datetime.fromtimestamp(next_dispatch)` para passar explicitamente o timezone de Brasília (`UTC-3`):
  ```python
  tz_br = timezone(timedelta(hours=-3))
  next_time_str = datetime.fromtimestamp(next_dispatch, tz=tz_br).strftime("%H:%M:%S")
  ```
- Isso garante que a string de previsão do próximo envio corresponda ao horário correto de Brasília (fuso padrão do usuário e do navegador), eliminando a falsa impressão de atraso.

---

## 🧪 Impacto e Testes

- **API**: A API agora aceita perfeitamente cargas de configurações com delays altos, sem retornar erros HTTP 422.
- **Painel e Robô**: O robô carrega o delay maior configurado pelo usuário, e os logs no painel do cliente passam a exibir a hora exata local de Brasília para o próximo disparo, mantendo coerência visual total com o cabeçalho dos logs.
