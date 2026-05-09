# 🌐 Configuração DNS - bluebotapp.com.br

## Servidor: Hostinger

### Passo 1: Acessar Painel
1. Login em https://br.hostinger.com/
2. Ir em **Websites** → **Gerenciar**
3. Acessar **Domínios** → **DNS / Nameservers**

### Passo 2: Configurar Registros DNS

| Tipo  | Nome/Host           | Valor/Aponta Para          | TTL     |
|-------|---------------------|----------------------------|---------|
| A     | @                   | [IP_DO_SEU_SERVIDOR]       | 1 hora  |
| A     | www                 | [IP_DO_SEU_SERVIDOR]       | 1 hora  |
| A     | api                 | [IP_DO_SEU_SERVIDOR]       | 1 hora  |
| A     | console             | [IP_DO_SEU_SERVIDOR]       | 1 hora  |
| A     | app                 | [IP_DO_SEU_SERVIDOR]       | 1 hora  |
| AAAA  | @                   | [IPV6, se aplicável]       | 1 hora  |
| CNAME | www (opcional)      | bluebotapp.com.br          | 1 hora  |

### Passo 3: Nameservers (Opcional)
Se preferir usar nameservers próprios:
- ns1.bluebotapp.com.br
- ns2.bluebotapp.com.br

### Passo 4: Verificação
Após configurar, aguarde a propagação DNS (até 48h, geralmente 1-2h)

Verifique com:
```bash
nslookup bluebotapp.com.br
dig bluebotapp.com.br
```

## 🔒 Obter Certificado SSL Let's Encrypt

### No servidor:
```bash
cd /caminho/para/bluebot

# Parar nginx temporariamente
docker compose stop nginx

# Obter certificado
docker run -it --rm \
  -v $(pwd)/ssl:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d bluebotapp.com.br \
  -d www.bluebotapp.com.br \
  -d api.bluebotapp.com.br \
  -d console.bluebotapp.com.br \
  -d app.bluebotapp.com.br \
  --email email@seuemail.com \
  --agree-tos \
  --no-eff-email

# Iniciar nginx
docker compose start nginx
```

### Renovação Automática
O container `certbot` já está configurado para renovar automaticamente.

## 🚀 Deploy

```bash
# 1. Build e deploy
chmod +x deploy.sh
./deploy.sh

# 2. Ou manualmente
docker compose up -d --build

# 3. Verificar logs
docker compose logs -f
```

## ✅ URLs Após Deploy

- **Site:** https://bluebotapp.com.br
- **API:** https://api.bluebotapp.com.br
- **Painel de Administração:** https://console.bluebotapp.com.br
- **Painel Cliente:** https://app.bluebotapp.com.br
- **Admin API:** https://bluebotapp.com.br/admin
- **Swagger (dev):** https://api.bluebotapp.com.br/docs

## 🔧 Troubleshooting

### Certificado não é confiável
- Aguarde propagação DNS
- Verifique se apontou para IP correto
- Se testando local, aceite exceção de segurança

### API inacessível
```bash
docker compose logs api
docker compose logs nginx
curl http://localhost:8000/health
```

### Renovar certificado manualmente
```bash
docker run -it --rm \
  -v $(pwd)/ssl:/etc/letsencrypt \
  certbot/certbot renew --force-renewal
```

## 📄 Documentação

- [Let's Encrypt](https://letsencrypt.org/)
- [Hostinger DNS](https://suporte.hostinger.com.br/artigos/33-como-alterar-servidores-dns-no-hostinger)
- [Nginx SSL](https://nginx.org/en/docs/http/configuring_https_servers.html)
