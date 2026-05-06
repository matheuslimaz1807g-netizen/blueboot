# REGISTRO DE MUDANÇAS - CONFIGURAÇÃO HTTPS

**Data:** 2026-05-06 20:40  
**Sessão:** 3 - Implementação HTTPS  
**Tipo:** Infraestrutura / Segurança

---

## RESUMO

Configuração completa de HTTPS para o domínio bluebotapp.com.br utilizando Let's Encrypt e Nginx. Inclui redirecionamento HTTP→HTTPS, subdomínios e renovação automática.

---

## MUDANÇAS REALIZADAS

### 1. Configuração Nginx (nginx.conf)
- **Adicionado:** Redirecionamento HTTP (porta 80) → HTTPS (porta 443)
- **Adicionado:** Múltiplos blocos server para domínios:
  - `bluebotapp.com.br` - Site principal
  - `www.bluebotapp.com.br` - Alias
  - `api.bluebotapp.com.br` - API dedicada
  - `painel.bluebotapp.com.br` - Painel admin
- **Adicionado:** HSTS (Strict-Transport-Security) - 1 ano
- **Atualizado:** Headers de segurança
- **Adicionado:** Configurações SSL/TLS (TLSv1.2+, TLSv1.3)
- **Adicionado:** Suporte a HTTP/2

### 2. Docker Compose (docker-compose.yml)
- **Adicionado:** Container `certbot` para renovação automática
- **Adicionado:** Volume `certbot_data` para certificados
- **Adicionado:** Volume `certbot/www` para desafios ACME
- **Atualizado:** Bot usa `https://api.bluebotapp.com.br`
- **Atualizado:** Removida montagem do Brave (já feita anteriormente)
- **Adicionado:** Volume `certbot_data` no nginx

### 3. Variáveis de Ambiente
- **Atualizado:** `.env` - `APRO_API_BASE=https://api.bluebotapp.com.br`
- **Atualizado:** `.env.bak` - `API_BASE_URL=https://api.bluebotapp.com.br`
- **Atualizado:** `api/app/core/config.py` - `API_BASE_URL=https://api.bluebotapp.com.br`

### 4. Scripts Criados
- **`setup-ssl.sh`** - Gera certificados SSL (teste/produção)
- **`deploy.sh`** - Automatiza deploy completo com HTTPS
- **`DNS_SETUP.md`** - Documentação de configuração DNS Hostinger

### 5. Configuração SSL
- **Diretórios criados:**
  - `./ssl/` - Certificados SSL
  - `./certbot/www/` - Desafios ACME
  - `./certbot_data/` - Volume Docker certbot

---

## ARQUIVOS MODIFICADOS

1. `nginx.conf` - Configuração HTTPS completa
2. `docker-compose.yml` - Adicionado certbot, volumes SSL
3. `.env` - URL API atualizada
4. `.env.bak` - URL API atualizada
5. `api/app/core/config.py` - API base URL

## ARQUIVOS CRIADOS

1. `setup-ssl.sh` - Script SSL
2. `deploy.sh` - Script deploy
3. `DNS_SETUP.md` - Documentação DNS
4. `./ssl/` - Diretório certificados
5. `./certbot/` - Diretório desafios ACME

---

## INSTRUÇÕES DE DEPLOY

### Pré-requisitos
1. DNS configurado (apontar para IP do servidor)
2. Docker e Docker Compose instalados
3. Portas 80 e 443 liberadas no firewall

### Passo a Passo

#### 1. Configurar DNS (Hostinger)
```bash
# Acessar: https://br.hostinger.com/
# Domínios → DNS / Nameservers
# Adicionar registros A:
#   @     → IP_DO_SERVIDOR
#   www   → IP_DO_SERVIDOR
#   api   → IP_DO_SERVIDOR
#   painel → IP_DO_SERVIDOR
```

#### 2. Aguardar propagação
```bash
# Verificar DNS
dig bluebotapp.com.br
# Aguardar até resolver para o IP correto
```

#### 3. Executar deploy
```bash
cd /caminho/bluebot

# Opção 1: Script automatizado
chmod +x deploy.sh
./deploy.sh

# Opção 2: Manual
docker compose up -d --build
```

#### 4. Obter certificado real (após DNS propagado)
```bash
docker run -it --rm \
  -v $(pwd)/ssl:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d bluebotapp.com.br \
  -d www.bluebotapp.com.br \
  -d api.bluebotapp.com.br \
  -d painel.bluebotapp.com.br \
  --email email@seuemail.com \
  --agree-tos \
  --no-eff-email
```

#### 5. Reiniciar nginx
```bash
docker compose restart nginx
```

#### 6. Verificar
```bash
# Testar HTTPS
curl -I https://bluebotapp.com.br

# Testar API
curl -I https://api.bluebotapp.com.br/health

# Verificar certificado
openssl s_client -connect bluebotapp.com.br:443 -servername bluebotapp.com.br
```

---

## URLs Após Deploy

| URL | Descrição |
|-----|-----------|
| https://bluebotapp.com.br | Site principal (redireciona para painel/admin) |
| https://www.bluebotapp.com.br | Site (alias) |
| https://api.bluebotapp.com.br | API REST |
| https://painel.bluebotapp.com.br | Painel administração |
| https://bluebotapp.com.br/admin | API Admin docs |

---

## SEGURANÇA

### Certificado Auto-assinado (Testes)
Para desenvolvimento/local, o script gera certificado auto-assinado.
**Aviso:** Navegadores mostrarão alerta de segurança.

### Certificado Let's Encrypt (Produção)
Para produção, obter certificado real:
- Gratuito
- Renovação automática configurada
- Confiável por todos navegadores

### Renovação Automática
O container `certbot` executa renovação a cada 12h:
```bash
docker compose logs certbot
```

---

## TROUBLESHOOTING

### Problema: "ERR_CERT_AUTHORITY_INVALID"
**Solução:** Aguardar DNS ou aceitar exceção (apenas testes)

### Problema: "502 Bad Gateway"
**Solução:** 
```bash
docker compose logs api
docker compose restart api
```

### Problema: Certificado expirado
**Solução:**
```bash
docker run -it --rm \
  -v $(pwd)/ssl:/etc/letsencrypt \
  certbot/certbot renew --force-renewal
```

### Problema: DNS não resolve
**Solução:**
1. Verificar no painel Hostinger
2. Esperar propagação (até 48h)
3. Limpar cache DNS: `ipconfig /flushdns` (Windows)

---

## PRÓXIMOS PASSOS

- [ ] Configurar DNS na Hostinger
- [ ] Aguardar propagação
- [ ] Executar deploy
- [ ] Obter certificado Let's Encrypt
- [ ] Testar todas as URLs
- [ ] Atualizar documentação para clientes

---

**Status:** ✅ Pronto para deploy  
**Data:** 2026-05-06  
**Próxima renovação SSL:** Automática (a cada 90 dias)
