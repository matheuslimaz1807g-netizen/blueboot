# BlueBot — Troubleshooting

## ERR_CERT_COMMON_NAME_INVALID

**Causa**: Paths SSL errados no nginx.conf ou certificado não cobre o subdomínio.

**Diagnóstico**:
```bash
# Verificar qual cert o Nginx está usando
docker exec bluebot_nginx nginx -T 2>/dev/null | grep ssl_certificate
# Verificar SANs do certificado
openssl x509 -in data/ssl/live/bluebotapp.com.br/fullchain.pem -text -noout | grep -A1 "Subject Alternative Name"
```

**Correção**:
```bash
bash scripts/renew-ssl.sh --new
docker compose restart nginx
```

## 502 Bad Gateway

**Causa**: API não está rodando ou nome do container errado no proxy_pass.

**Diagnóstico**:
```bash
docker compose ps api
docker compose logs api --tail 50
curl http://localhost:8000/health
```

## CORS Bloqueado

**Causa**: Origin não está na lista de permitidos.

**Correção**: Verificar `nginx/snippets/cors.conf` e `api/app/main.py` (allowed_origins).

## Container não sobe

```bash
# Ver logs
docker compose logs <service> --tail 100
# Verificar .env
docker compose config  # Mostra config expandida
# Rebuild
docker compose build --no-cache <service>
docker compose up -d <service>
```

## Certificado expirado

```bash
# Verificar expiração
openssl x509 -in data/ssl/live/bluebotapp.com.br/fullchain.pem -noout -dates
# Renovar
bash scripts/renew-ssl.sh --new
```

## Disco cheio

```bash
# Limpar Docker
docker system prune -af --volumes
# Limpar backups antigos
find data/backups -mtime +7 -delete
# Limpar logs
docker compose logs --no-log-prefix 2>/dev/null | head -0  # Truncar
```

## Cliente não conecta à API

```bash
# Verificar rede
docker network inspect bluebot_network
# Testar conectividade de dentro do container
docker exec bot_<slug> curl -s http://bluebot_api:8000/health
```
