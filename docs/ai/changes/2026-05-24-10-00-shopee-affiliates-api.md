# Log de Mudanças: API Oficial de Afiliados da Shopee GraphQL

## Mudanças Realizadas

1. **Integração com a API Oficial da Shopee (`executable/affiliates/shopee.py`)**:
   - Refatorada a função `convert` para suportar autenticação baseada em criptografia e requisições GraphQL diretamente na API oficial de afiliados da Shopee (`https://open-api.affiliate.shopee.com.br/graphql`).
   - Implementado o parser inteligente para extrair `APPID` e `SECRET` a partir do campo único `shopee_token` que aceita os formatos `APPID:SECRET` e `APPID|SECRET`.
   - Adicionada computação segura de assinatura SHA256 baseada em timestamp Unix e payload JSON minificado, garantindo consistência com os requisitos de assinatura da Shopee.

2. **Resiliência e Mecanismo de Fallback**:
   - Para evitar interrupções de fluxo causadas por credenciais mal formatadas, limites de cota da API ou quedas no servidor da Shopee, o conversor agora executa um fallback transparente para a lógica legada baseada em injeção de parâmetros UTM/ULS e encurtadores TinyURL/Is.gd.

3. **Atualização do Pipeline de Processamento (`executable/pipeline.py`)**:
   - Modificado o fluxo de conversão da Shopee para repassar o `shopee_token` descriptografado da licença (`config.get("shopee_token")`) como segundo argumento na chamada a `shopee.convert()`.

## Razão para Cada Mudança
- **Comissões Garantidas**: A API oficial da Shopee GraphQL garante que os links gerados redirecionem através dos cookies corretos de afiliado da Shopee, assegurando o comissionamento do proprietário do BlueBot de forma profissional.
- **Resiliência contra Quedas**: No caso de instabilidade da API oficial da Shopee, o bot continuará processando e postando ofertas normalmente sem quebrar, caindo de volta para a injeção tradicional de parâmetros.

## Testes Realizados e Validados
- **Testes Unitários de Conectividade**: Validamos que a geração da assinatura bate perfeitamente com a especificação da Shopee e que a chamada à API retorna o short link encurtado oficial `s.shopee.com.br`.
- **Testes de Fallback**: Validamos que se um token for inválido, em branco ou estiver ausente, a função converte e encurta via TinyURL graciosamente sem gerar exceções.
