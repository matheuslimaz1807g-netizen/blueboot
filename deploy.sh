#!/bin/bash
# deploy.sh - Deploy completo com HTTPS para bluebotapp.com.br
# Requisitos: Docker, Docker Compose, DNS configurado

set -e

DOMAIN="bluebotapp.com.br"
API_DOMAIN="api.bluebotapp.com.br"
CONSOLE_DOMAIN="console.bluebotapp.com.br"
APP_DOMAIN="app.bluebotapp.com.br"

echo "🚀 BlueBot Deploy - HTTPS Setup"
echo "================================="
echo ""

# Passo 1: Backup
echo "📦 Passo 1: Criando backup..."
git stash push -m "PRE-DEPLOY-$(date +%Y%m%d-%H%M): Antes do deploy HTTPS"
echo "✅ Backup criado"

# Passo 2: Build
echo ""
echo "🏗️  Passo 2: Buildando containers..."
docker compose build --no-cache
echo "✅ Build concluído"

# Passo 3: Iniciar serviços (sem HTTPS primeiro para validação)
echo ""
echo "🐳 Passo 3: Iniciando serviços..."
docker compose up -d postgres api nginx
echo "✅ Serviços iniciados"

# Passo 4: Esperar API ficar saudável
echo ""
echo "⏳ Passo 4: Aguardando API ficar saudável..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API saudável!"
    break
  fi
  echo "  Tentativa $i/30..."
  sleep 2
done

# Passo 5: Configurar HTTPS
echo ""
echo "🔒 Passo 5: Configurando HTTPS..."

# Gerar certificado via Let's Encrypt (requer DNS apontado)
echo "Para HTTPS real, execute:"
echo "  docker run -it --rm \\"
echo "    -v \$(pwd)/ssl:/etc/letsencrypt \\"
echo "    -v \$(pwd)/certbot/www:/var/www/certbot \\"
echo "    certbot/certbot certonly --webroot \\"
echo "    -w /var/www/certbot \\"
echo "    -d ${DOMAIN} -d www.${DOMAIN} \\"
echo "    -d ${API_DOMAIN} -d ${CONSOLE_DOMAIN} \\"
echo "    -d ${APP_DOMAIN}"
echo ""

# Para testes, usar certificado auto-assinado
if [ ! -f "./ssl/fullchain.pem" ]; then
  echo "⚠️  Gerando certificado auto-assinado para testes..."
  mkdir -p ./ssl
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ./ssl/privkey.pem \
    -out ./ssl/fullchain.pem \
    -subj "/C=BR/ST=SP/L=Sao Paulo/O=BlueBot/CN=${DOMAIN}" 2>/dev/null
  echo "✅ Certificado auto-assinado gerado"
fi

# Restart nginx com SSL
docker compose restart nginx
echo "✅ Nginx reiniciado com HTTPS"

# Passo 6: Iniciar outros serviços
echo ""
echo "📡 Passo 6: Iniciando serviços restantes..."
docker compose up -d whatsapp bot
echo "✅ Todos os serviços iniciados"

# Passo 7: Status
echo ""
echo "📊 Passo 7: Status dos serviços"
docker compose ps

# Passo 8: URLs
echo ""
echo "🌐 URLs:"
echo "  🔒 HTTPS: https://${DOMAIN}"
echo "  🔒 HTTPS: https://${API_DOMAIN}"
echo "  🔒 HTTPS: https://${CONSOLE_DOMAIN}"
echo "  🔒 HTTPS: https://${APP_DOMAIN}"
echo "  ⚠️  Aviso: Se usar certificado auto-assinado, aceite o aviso de segurança no navegador"
echo ""
echo "✅ Deploy concluído!"
echo ""
echo "📝 Próximos passos:"
echo "  1. Aponte DNS para IP do servidor"
echo "  2. Obtenha certificado Let's Encrypt real"
echo "  3. Atualize APRO_API_BASE se necessário"
