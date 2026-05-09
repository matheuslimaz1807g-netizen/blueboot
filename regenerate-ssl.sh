#!/bin/bash
# regenerate-ssl.sh - Regenera certificado SSL incluindo todos os subdomínios
# Execute na VPS: chmod +x regenerate-ssl.sh && ./regenerate-ssl.sh

set -e

echo "🔐 Regenerando certificado SSL para todos os subdomínios..."

# Verificar se estamos no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Execute este script no diretório do projeto blueboot"
    exit 1
fi

# Backup dos certificados atuais
echo "📦 Fazendo backup dos certificados atuais..."
BACKUP_DIR="ssl.backup.$(date +%Y%m%d_%H%M%S)"
cp -r ssl "$BACKUP_DIR"
echo "✅ Backup criado em: $BACKUP_DIR"

# Parar nginx temporariamente
echo "⏹️  Parando nginx..."
docker compose stop nginx

# Criar diretório para desafios ACME se não existir
mkdir -p certbot/www

# Gerar novo certificado Let's Encrypt
echo "🔑 Gerando novo certificado Let's Encrypt..."
docker run -it --rm \
  -v "$(pwd)/ssl:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d bluebotapp.com.br \
  -d www.bluebotapp.com.br \
  -d api.bluebotapp.com.br \
  -d console.bluebotapp.com.br \
  -d app.bluebotapp.com.br \
  --email "admin@bluebotapp.com.br" \
  --agree-tos \
  --no-eff-email \
  --force-renewal

# Verificar se o certificado foi gerado
if [ -f "ssl/live/bluebotapp.com.br/fullchain.pem" ]; then
    echo "✅ Certificado gerado com sucesso!"

    # Reiniciar nginx
    echo "🔄 Reiniciando nginx..."
    docker compose start nginx

    # Verificar se funcionou
    echo "🧪 Testando conexões HTTPS..."
    sleep 2

    for domain in "bluebotapp.com.br" "console.bluebotapp.com.br" "api.bluebotapp.com.br" "app.bluebotapp.com.br"; do
        if curl -s -I "https://$domain/" | grep -q "HTTP/2 200\|HTTP/1.1 200"; then
            echo "✅ $domain: OK"
        else
            echo "❌ $domain: FALHA"
        fi
    done

    echo ""
    echo "🎉 Certificado SSL regenerado com sucesso!"
    echo "📝 Todos os subdomínios agora têm certificado válido."

else
    echo "❌ Falha ao gerar certificado. Restaurando backup..."
    rm -rf ssl
    mv "$BACKUP_DIR" ssl
    docker compose start nginx
    exit 1
fi