# PLANEJAMENTO DETALHADO - Subdomínios Admin e Clientes

## Data: 2026-05-08 16:00
## Tipo: Arquitetura de subdomínios / DNS / SSL

---

## 1. ANÁLISE DA SITUAÇÃO ATUAL

### Contexto
- A decisão é usar `console.bluebotapp.com.br` como domínio administrativo.
- O frontend cliente ficará centralizado em `app.bluebotapp.com.br` sem identificadores de usuário na URL.
- A autenticação e o isolamento de dados serão geridos por JWT no backend.
- As referências residuais a `painel.bluebotapp.com.br` foram removidas de scripts e documentação de DNS.

### Estado do sistema
- `nginx.conf` já direciona `bluebotapp.com.br` e `www.bluebotapp.com.br` para `console.bluebotapp.com.br`.
- O bloco de serviço `console.bluebotapp.com.br` está configurado para servir o painel admin estático e proxyar `/admin/` para a API.
- `app.bluebotapp.com.br` já tem bloco separado no Nginx para o painel centralizado do cliente.
- A documentação de DNS e os scripts de emissão de certificado agora usam `console` e `app` como domínios ativos.

---

## 2. PROBLEMAS IDENTIFICADOS

### [ALTO] Resíduos de `painel.bluebotapp.com.br`
- Impacto: confusão operacional, falhas de certificação e DNS desnecessário.
- Esforço: BAIXO.

### [MÉDIO] Necessidade de alinhar Cloudflare com a nova topologia
- Impacto: emissão de SSL e roteamento podem falhar se registros estiverem inconsistentes.
- Esforço: BAIXO/MÉDIO.

### [MÉDIO] Garantir roteamento seguro para admin e app
- Impacto: erros de CORS ou roteamento incorreto na aplicação.
- Esforço: MÉDIO.

---

## 3. SOLUÇÃO PROPOSTA

### Etapa 1: Alinhar DNS/Cloudflare aos subdomínios ativos
- Confirmar na zona Cloudflare os seguintes registros DNS:
  - `A @ -> 177.7.49.248`
  - `CNAME www -> bluebotapp.com.br` ou `A www -> 177.7.49.248`
  - `A api -> 177.7.49.248`
  - `A console -> 177.7.49.248`
  - `A app -> 177.7.49.248`
- Remover qualquer registro `painel.bluebotapp.com.br` do DNS.
- Configurar Cloudflare em modo DNS-only (cinza) para `console`, `api`, `app` durante emissão de SSL via webroot.
- Definir TLS em Cloudflare como `Full` ou `Full (strict)` após o certificado ser emitido.

### Etapa 2: Atualizar documentação e scripts para a topologia final
- `DNS_SETUP.md`: remover `painel` e documentar `console` + `app`.
- `setup-ssl.sh`: remover `-d painel.bluebotapp.com.br` e manter só domínios ativos.
- `deploy.sh`: remover `PAINEL_DOMAIN` e atualizar a lista de domínios de certificado.
- `docs/ai/changes/2026-05-06-20-40-https-configuracao.md`: alinhar a documentação histórica se necessário.

### Etapa 3: Validar Nginx e roteamento atual
- Revisar `nginx.conf` para confirmar:
  - `console.bluebotapp.com.br` está ativo no bloco administrativo.
  - `app.bluebotapp.com.br` está ativo no bloco do cliente.
  - `bluebotapp.com.br` / `www` redirecionam para `console`.
  - o bloco de desafio ACME em HTTP está presente para `/.well-known/acme-challenge/`.

### Etapa 4: Emitir certificado Let’s Encrypt para os domínios válidos
- Domínios finais para emissão:
  - `bluebotapp.com.br`
  - `www.bluebotapp.com.br`
  - `api.bluebotapp.com.br`
  - `console.bluebotapp.com.br`
  - `app.bluebotapp.com.br` (se necessário para o cliente)
- Usar o mesmo webroot montado em `./certbot/www` e nginx com DNS-only enquanto emite.
- Reiniciar `nginx` após emissão.

---

## 4. CRONOGRAMA DE IMPLEMENTAÇÃO

### Sessão 1 - Verificação e alinhamento DNS/Cloudflare
- [ ] Confirmar registros Cloudflare ativos.
- [x] Remover `painel.bluebotapp.com.br`.
- [ ] Garantir `console`, `app`, `api`, `www` válidos.

### Sessão 2 - Ajuste de scripts e documentação
- [x] Atualizar `DNS_SETUP.md`.
- [x] Atualizar `setup-ssl.sh`.
- [x] Atualizar `deploy.sh`.
- [x] Atualizar documentação de mudanças / histórico se necessário.

### Sessão 3 - Validação Nginx e SSL
- [ ] Verificar `nginx.conf`.
- [ ] Emitir certificado para domínios ativos.
- [ ] Validar acesso HTTPS em `console`, `app` e `api`.

---

## 5. RISCOS E MITIGAÇÃO

### Risco: Domínio `painel` ainda presente no DNS
- Mitigação: remover o registro e usar apenas domínios ativos.

### Risco: Cloudflare proxy (orange cloud) bloqueando webroot
- Mitigação: usar DNS-only para emissão ou adotar desafio DNS se preferir Cloudflare proxy.

### Risco: rota de `app` mal configurada
- Mitigação: validar com `curl` em `app.bluebotapp.com.br` e revisar o bloco Nginx.

---

## 6. CRITÉRIOS DE SUCESSO

- [ ] Cloudflare DNS atualizado com `console`, `app`, `api`, `www`, `@`.
- [ ] Registro `painel.bluebotapp.com.br` removido.
- [ ] `nginx.conf` validado para admin e cliente.
- [ ] SSL emitido para domínios ativos.
- [ ] `setup-ssl.sh` e `deploy.sh` alinhados com a topologia final.
- [ ] Documentação de DNS atualizada.

---

## 7. ARQUIVOS E CONFIGURAÇÕES QUE SERÃO ALTERADOS

### Arquivos do repositório
- `nginx.conf`
- `DNS_SETUP.md`
- `setup-ssl.sh`
- `deploy.sh`
- `docs/ai/changes/2026-05-06-20-40-https-configuracao.md` (opcional)
- `docs/ai/plans/2026-05-08-16-00-subdominios-admin-clientes.md`

### Configurações externas
- Cloudflare DNS zone para `bluebotapp.com.br`
- Cloudflare proxy/TLS settings (modo DNS-only durante emissão, TLS `Full` ou `Full (strict)` após emissão)

---

## 8. PRÓXIMO PASSO

Aguardar sua confirmação para aplicar a Etapa 1.

**Etapa 1 proposta:**
- Ajustar Cloudflare DNS de acordo com os domínios ativos
- Validar que `console`, `app`, `api`, `www` resolvem para `177.7.49.248`
- Remover `painel.bluebotapp.com.br` do DNS
- Confirmar que o Nginx atual está consistente com essa topologia
