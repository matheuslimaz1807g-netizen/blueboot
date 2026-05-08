#!/bin/bash
# setup-ssl.sh - Configura SSL com Let's Encrypt para bluebotapp.com.br
# Execute: chmod +x setup-ssl.sh && ./setup-ssl.sh

set -e

echo "🔐 Configurando SSL para bluebotapp.com.br..."

# Criar diretório para desafios ACME
mkdir -p ./certbot/www

# Iniciar nginx para desafios HTTP
mkdir -p ./ssl

# Gerar certificado auto-assinado temporário (para testes iniciais)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./ssl/privkey.pem \
  -out ./ssl/fullchain.pem \
  -subj "/C=BR/ST=SP/L=Sao Paulo/O=BlueBot/OU=Development/CN=bluebotapp.com.br"

echo "✅ Certificado temporário gerado"
echo ""
echo "📝 Para obter certificado real Let's Encrypt:"
echo "   1. Aponte o DNS bluebotapp.com.br para este servidor"
echo "   2. Execute no servidor:"
echo "   docker run -it --rm \\"
echo "     -v \$(pwd)/ssl:/etc/letsencrypt \\"
echo "     -v \$(pwd)/certbot/www:/var/www/certbot \\"
echo "     certbot/certbot certonly --webroot \\"
echo "     -w /var/www/certbot \\"
echo "     -d bluebotapp.com.br \\"
echo "     -d www.bluebotapp.com.br \\"
echo "     -d api.bluebotapp.com.br \\"
echo "     -d painel.bluebotapp.com.br \\"
echo "     -d console.bluebotapp.com.br"
echo ""
echo "✅ Setup concluído!"
