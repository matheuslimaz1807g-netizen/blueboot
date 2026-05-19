# Mudanças Realizadas: Enriquecimento de Logs de Atividades do Cliente

**Data/Hora**: 2026-05-19 10:40

## Mudanças Realizadas
1. **Retorno de Metadados no Pipeline (`executable/pipeline.py`)**:
   - Atualizada a assinatura e retornos do método `processar_mensagem` para entregar um 4-tuple que inclui o dicionário `promotion_data`.
   - Modificados todos os fluxos de sucesso e erro do pipeline para suportar este novo retorno.

2. **Formatação Premium de Log no Bot Runner (`executable/bot_runner.py`)**:
   - O callback de atividade do cliente (`self._activity`) agora utiliza os metadados de promoção para montar uma descrição rica em formato premium.
   - Mostra:
     - 📦 Ícone de caixa seguido pelo **título/nome limpo do produto**, limitado em tamanho, e a **loja de origem** (ex: AliExpress, Shopee, Mercado Livre).
     - 💰 **Preço/Valor** real capturado.
     - ✅ Status e destinos de entrega com o total diário.
     - ⏱️ **Previsão exata de horário** no qual o próximo envio do Python estará liberado.

## Testes Realizados
- Ambos os arquivos compilados com sucesso via `python -m py_compile` sem erros.

## Impacto na Aplicação
- O painel do cliente agora exibe detalhes minuciosos e premium de cada produto enviado, oferecendo total transparência e uma interface profissional.
