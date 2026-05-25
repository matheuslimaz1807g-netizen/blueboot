# Mudancas: shortlink oficial Shopee via GraphQL

## Mudancas realizadas

- Reimplementado `executable/affiliates/shopee.py` para usar a API oficial:
  - endpoint `https://open-api.affiliate.shopee.com.br/graphql`;
  - mutation `generateShortLink`;
  - assinatura SHA256 com `APPID + timestamp + payload + SECRET`;
  - header `Authorization: SHA256 Credential=..., Timestamp=..., Signature=...`.
- `shopee_token` passa a aceitar `APPID:SECRET` ou `APPID|SECRET`.
- `pipeline.py` agora passa `config.get("shopee_token", "")` para `shopee.convert()`.
- Mensagem de credencial ausente atualizada para `APPID/SECRET`.
- Labels do painel cliente, admin e painel local atualizadas para `Shopee APPID:SECRET`.
- Removido fallback para TinyURL/is.gd na Shopee para evitar envio de link que pareca afiliado sem conversao oficial.
- Adicionado teste estatico `test_shopee_official_shortlink_static.py`.

## Razao

Garantir que ofertas Shopee sejam convertidas pela API oficial de afiliados usando as credenciais informadas pelo cliente no painel, em vez de apenas injetar parametros ou encurtar URL comum.

## Testes adicionados/modificados

- `api/tests/test_shopee_official_shortlink_static.py`

## Validacao executada

- `python -m py_compile` em:
  - `executable/affiliates/shopee.py`
  - `executable/pipeline.py`
  - `api/tests/test_shopee_official_shortlink_static.py`
- Checagem estatica via Node REPL confirmando:
  - endpoint GraphQL oficial;
  - mutation `generateShortLink`;
  - assinatura SHA256;
  - header Authorization;
  - ausencia de TinyURL/is.gd;
  - pipeline passando credencial Shopee.
- `new Function` nos scripts inline de `client_app/index.html` e `admin/index.html`: OK.

## Validacao bloqueada

- Import runtime local de `shopee.py` nao executou no Python empacotado porque `httpx` nao esta instalado nesse runtime; o projeto declara `httpx==0.27.0` em `executable/requirements.txt`.
- `pytest` segue indisponivel no ambiente local.

## Impacto

- Cliente deve preencher o campo Shopee como `APPID:SECRET`.
- Se a oferta for Shopee e a credencial estiver correta, o bot substitui o link pelo `shortLink` oficial.
- Se a credencial estiver ausente/incorreta ou a API oficial falhar, a conversao falha e o modo estrito evita enviar uma oferta sem link afiliado real.
