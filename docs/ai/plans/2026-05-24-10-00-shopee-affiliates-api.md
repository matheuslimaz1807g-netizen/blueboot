# Planejamento: Integração Oficial com API GraphQL de Afiliados da Shopee

## 1. Análise da Situação Atual
Atualmente, o conversor de links da Shopee em `executable/affiliates/shopee.py` apenas injeta parâmetros manuais de rastreamento na query string da URL expandida e depois encurta usando serviços públicos gratuitos (TinyURL ou Is.gd). Essa abordagem rudimentar não utiliza a API oficial da Shopee e, portanto, não gera comissões reais do programa de afiliados oficial de forma garantida para todos os formatos de links.

O usuário forneceu um exemplo funcional testado via `curl` de requisição GraphQL na API oficial de afiliados da Shopee (`https://open-api.affiliate.shopee.com.br/graphql`).

## 2. Abordagem Técnica Proposta

### A. Formato de Token da Shopee
Como a tabela do banco de dados e os formulários do painel possuem apenas um único campo `shopee_token` (tipo texto), o usuário informará as credenciais completas no formato:
`APPID:SECRET` ou `APPID|SECRET`
Exemplo: `18368521053:R5AQDY62FCX5ICIOD73HS3I5RTQEIG5J`

O conversor de Shopee irá ler essa string, quebrar no caractere `:` ou `|` e extrair as duas credenciais necessárias para autenticação e assinatura.

### B. Assinatura e Autenticação GraphQL
Implementaremos a lógica de criptografia em Python equivalente ao script bash do usuário:
1. Obter o timestamp Unix atual (`int(time.time())`).
2. Montar o payload JSON em string minificada sem espaços desnecessários (para bater perfeitamente a assinatura):
   `payload = {"query": "mutation { generateShortLink(input:{ originUrl:\"...\", subIds:[\"s1\",\"s2\",\"s3\",\"s4\",\"s5\"] }) { shortLink }}"}`
3. Criar a string concatenada `factor`:
   `factor = APPID + TIMESTAMP + PAYLOAD + SECRET`
4. Computar o hash SHA256 (hex digest) da string concatenada:
   `signature = hashlib.sha256(factor.encode('utf-8')).hexdigest()`
5. Configurar os cabeçalhos HTTP:
   `Authorization: SHA256 Credential=APPID, Timestamp=TIMESTAMP, Signature=SIGNATURE`
   `Content-Type: application/json`
6. Enviar uma requisição HTTP POST assíncrona usando `httpx` para `https://open-api.affiliate.shopee.com.br/graphql`.

### C. Estratégia de Fallback Seguro (Resiliência)
Caso a API da Shopee retorne erro, o token seja inválido, ou haja instabilidade de rede, o conversor **automaticamente cairá de volta (fallback)** para a lógica original de injeção de parâmetros manuais e encurtador externo. Isso impede que o fluxo de processamento de mensagens pare, garantindo robustez operacional de 100%.

## 3. Cronograma de Implementação
- **Passo 1**: Executar o backup de segurança com Git Stash.
- **Passo 2**: Atualizar o arquivo `executable/affiliates/shopee.py` com a lógica oficial da API GraphQL e o mecanismo de fallback robusto.
- **Passo 3**: Atualizar `executable/pipeline.py` para passar o token decriptografado da Shopee para a função `shopee.convert()`.
- **Passo 4**: Testar as modificações gerando logs e atualizando logs de backups e log de mudanças.
