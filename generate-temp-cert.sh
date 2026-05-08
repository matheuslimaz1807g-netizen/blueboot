#!/bin/bash
# generate-temp-cert.sh - Gera certificado auto-assinado temporário para nginx
# Execute: chmod +x generate-temp-cert.sh && ./generate-temp-cert.sh

set -e

echo "🔐 Gerando certificado auto-assinado temporário..."

# Criar diretórios conforme docker-compose.yml
mkdir -p ssl/letsencrypt/live/bluebotapp.com.br certbot/www

# Gerar certificado auto-assinado
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/letsencrypt/live/bluebotapp.com.br/privkey.pem \
  -out ssl/letsencrypt/live/bluebotapp.com.br/fullchain.pem \
  -subj "/C=BR/ST=SP/L=Sao Paulo/O=BlueBot/CN=bluebotapp.com.br"

echo "✅ Certificado temporário gerado!"
echo "📍 Localização: ssl/letsencrypt/live/bluebotapp.com.br/"
echo ""
echo "🔄 Execute: docker compose restart nginx"