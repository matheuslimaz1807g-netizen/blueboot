# Plano: conversao oficial Shopee via GraphQL

## Analise da situacao atual

- `executable/affiliates/shopee.py` ainda injeta parametros UTM/ULS e usa encurtadores publicos.
- `executable/pipeline.py` detecta links Shopee, mas chama `shopee.convert(expanded_link)` sem repassar a credencial do painel.
- O painel ja possui um campo criptografado `shopee_token`, exposto no cliente/admin.
- Para evitar migration, o campo `shopee_token` sera usado para receber as credenciais no formato `APPID:SECRET` ou `APPID|SECRET`.

## Problemas identificados

1. [Critico] Conversao atual da Shopee nao usa a API oficial de afiliados.
   - Impacto: link pode nao gerar comissao real.
   - Esforco: medio.

2. [Alto] Pipeline nao passa a credencial Shopee para o conversor.
   - Impacto: mesmo com credencial no painel, o conversor nao consegue autenticar.
   - Esforco: baixo.

3. [Medio] UI chama o campo de "Shopee Token", mas o cliente precisa informar APPID e SECRET.
   - Impacto: risco de preenchimento incorreto.
   - Esforco: baixo.

## Solucao proposta

- Implementar assinatura oficial:
  - `timestamp = unix seconds`
  - `payload` JSON minificado contendo a mutation `generateShortLink`
  - `factor = APPID + timestamp + payload + SECRET`
  - `signature = sha256(factor)`
  - header `Authorization: SHA256 Credential=..., Timestamp=..., Signature=...`
- Implementar parser de credenciais em `shopee_token`.
- Alterar pipeline para chamar `shopee.convert(expanded_link, config.get("shopee_token", ""))`.
- Atualizar labels do painel para indicar `APPID:SECRET`.
- Criar testes estaticos de contrato.

## Riscos e mitigacao

- Risco: credencial mal formatada.
  - Mitigacao: erro claro no log e retorno sem conversao oficial.

- Risco: API Shopee indisponivel.
  - Mitigacao: nao enviar link falso como afiliado; o pipeline registra erro e o modo estrito impede o envio sem conversao real.

- Risco: secret exposto em logs.
  - Mitigacao: nunca logar APPID/SECRET.

## Criterios de sucesso

- Quando a oferta for Shopee e `conv_shopee=true`, o bot usa `generateShortLink`.
- APPID/SECRET informados no painel sao usados na assinatura.
- Pipeline substitui o link original pelo shortlink retornado.
- UI orienta o cliente a informar `APPID:SECRET`.
