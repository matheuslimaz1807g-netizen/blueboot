#!/bin/bash
# generate-temp-cert.sh - Gera certificado auto-assinado temporário para nginx
# Execute: chmod +x generate-temp-cert.sh && ./generate-temp-cert.sh

set -e

echo "🔐 Gerando certificado auto-assinado temporário..."

# Criar diretórios
mkdir -p ssl/live/bluebotapp.com.br certbot/www

# Gerar certificado auto-assinado
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/C=BR/ST=SP/L=Sao Paulo/O=BlueBot/CN=bluebotapp.com.br"

# Criar links simbólicos para compatibilidade com nginx.conf
ln -sf ../../../fullchain.pem ssl/live/bluebotapp.com.br/fullchain.pem
ln -sf ../../../privkey.pem ssl/live/bluebotapp.com.br/privkey.pem

echo "✅ Certificado temporário gerado!"
echo "📍 Localização: ssl/live/bluebotapp.com.br/"
echo ""
echo "🔄 Execute: docker compose restart nginx"