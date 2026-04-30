#!/bin/bash
# =============================================================================
# BlueBot — VPS Setup Script
# =============================================================================
# Run this script on a fresh Ubuntu 22.04+ VPS as root.
# It installs Docker, generates SSL certificates, and starts all services.
#
# Usage:
#   chmod +x setup_vps.sh
#   sudo ./setup_vps.sh
# =============================================================================

set -euo pipefail

echo "=========================================="
echo "  BlueBot VPS Setup"
echo "=========================================="

# ── 1. Update system ──────────────────────────────────────────────────────────
apt-get update && apt-get upgrade -y
apt-get install -y curl git ufw fail2ban

# ── 2. Configure firewall ────────────────────────────────────────────────────
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH
ufw --force enable

# ── 3. Install Docker ────────────────────────────────────────────────────────
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# ── 4. Generate SSL certificates (self-signed for initial setup) ─────────────
# For production, replace with Let's Encrypt:
#   apt-get install -y certbot python3-certbot-nginx
#   certbot --nginx -d seu-dominio.com
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/C=BR/ST=SP/L=SaoPaulo/O=BlueBot/CN=localhost"

echo "⚠️  Certificado SSL auto-assinado gerado."
echo "   Para produção, substitua por Let's Encrypt:"
echo "   certbot --nginx -d seu-dominio.com"

# ── 5. Configure .env ────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_USER=bluebot
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=bluebot

# ── API Security ──────────────────────────────────────────────────────────────
JWT_SECRET=$(openssl rand -base64 64)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 16)

# ── API ───────────────────────────────────────────────────────────────────────
API_BASE_URL=https://localhost
RATE_LIMIT_PER_MINUTE=60
APP_VERSION=1.0.0
EOF
    echo "✅ .env gerado com senhas aleatórias!"
    echo ""
    echo "⚠️  GUARDE ESTAS INFORMAÇÕES:"
    echo "   Admin user: admin"
    echo "   Admin password: $(grep ADMIN_PASSWORD .env | cut -d= -f2)"
    echo "   JWT Secret: $(grep JWT_SECRET .env | head -1 | cut -d= -f2)"
    echo ""
    echo "   Salve em um local seguro (ex: gerenciador de senhas)!"
fi

# ── 6. Start services ────────────────────────────────────────────────────────
docker compose up -d --build

echo ""
echo "=========================================="
echo "  ✅ BlueBot está rodando!"
echo "=========================================="
echo ""
echo "  Acesse: https://SEU_IP_VPS/admin/"
echo "  Login:  admin / $(grep ADMIN_PASSWORD .env | cut -d= -f2)"
echo ""
echo "  Para configurar HTTPS com Let's Encrypt:"
echo "  1. Aponte seu domínio para o IP da VPS"
echo "  2. Execute: certbot --nginx -d seu-dominio.com"
echo ""
echo "  Para ver logs: docker compose logs -f"
echo "=========================================="
