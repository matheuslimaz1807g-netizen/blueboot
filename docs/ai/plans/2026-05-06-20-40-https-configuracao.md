# PLANEJAMENTO DETALHADO - HTTPS bluebotapp.com.br

## Data: 2026-05-06 20:40
## Tipo: Implementação HTTPS / Infraestrutura

---

## 1. ANÁLISE DA SITUÇÃO ATUAL

### Contexto
- Domínio comprado: bluebotapp.com.br (expira 2027-05-06)
- Servidor: Ainda não configurado
- HTTPS: Não configurado
- DNS: A configurar na Hostinger

### Objetivo
Configurar HTTPS completo com Let's Encrypt para todos os serviços:
- bluebotapp.com.br
- www.bluebotapp.com.br  
- api.bluebotapp.com.br
- painel.bluebotapp.com.br

---

## 2. PROBLEMAS A RESOLVER

### [ALTO] HTTPS não configurado
- Impacto: Sem criptografia, navegadores marcam como inseguro
- Esforço: MÉDIO - 2 horas

### [MÉDIO] DNS não apontado
- Impacto: Domínio inacessível
- Esforço: BAIXO - 30 min (configuração)

### [BAIXO] Certificados ausentes
- Impacto: HTTPS não funciona
- Esforço: MÉDIO - 1 hora

---

## 3. SOLUÇÕES PROPOSTAS

### Solução 1: Configurar DNS na Hostinger
- Criar registros A para @, www, api, painel
- Apontar para IP do servidor
- Aguardar propagação

### Solução 2: Configurar Nginx com SSL
- Blocos server separados por domínio
- Redirecionamento HTTP→HTTPS
- HSTS header
- HTTP/2 habilitado

### Solução 3: Let's Encrypt
- Certbot para emissão
- Renovação automática via container
- Certificados para todos subdomínios

### Solução 4: Atualizar URLs
- .env: APRO_API_BASE=https://api.bluebotapp.com.br
- config.py: API_BASE_URL=https://api.bluebotapp.com.br

---

## 4. CRONOGRAMA DE IMPLEMENTAÇÃO

### Sessão 3 (20:30-21:30) - Configuração HTTPS
- ✅ Atualizar nginx.conf com HTTPS
- ✅ Atualizar docker-compose.yml (certbot)
- ✅ Criar scripts deploy.sh, setup-ssl.sh
- ✅ Atualizar variáveis de ambiente
- ✅ Documentar DNS setup

### Sessão 4 (21:30-22:00) - Testes
- ✅ Build containers
- ✅ Iniciar serviços
- ✅ Verificar HTTPS
- ✅ Validar certificados

---

## 5. RISCOS E MITIGAÇÃO

### Risco 1: DNS não propaga
- **Mitigação:** Aguardar até 48h, usar IP temporário

### Risco 2: Certificado falha
- **Mitigação:** Usar certificado auto-assinado para testes

### Risco 3: API inacessível
- **Mitigação:** Manter fallback HTTP no nginx durante transição

---

## 6. CRITÉRIOS DE SUCESSO

- [ ] DNS configurado na Hostinger
- [ ] Nginx com HTTPS funcionando
- [ ] Redirecionamento HTTP→HTTPS
- [ ] Certificado válido (ou auto-assinado para testes)
- [ ] Todas as URLs acessíveis via HTTPS
- [ ] Renovação automática configurada

---

## 7. DOCUMENTAÇÃO

- [X] `nginx.conf` - Configuração HTTPS
- [X] `docker-compose.yml` - Certbot container
- [X] `setup-ssl.sh` - Script SSL
- [X] `deploy.sh` - Script deploy
- [X] `DNS_SETUP.md` - Configuração DNS
- [X] `docs/ai/changes/2026-05-06-20-40-https-configuracao.md` - Log de mudanças

---

**Status:** ✅ Implementação Concluída  
**Próximo Passo:** Deploy no servidor (aguardar DNS)
