#!/bin/bash
# =============================================================================
# scripts/renew-ssl.sh — Renovar certificados Let's Encrypt
#
# Uso:
#   bash scripts/renew-ssl.sh              # Renovar existentes
#   bash scripts/renew-ssl.sh --new        # Gerar novos certificados
#   crontab: 0 4 * * 1 /opt/bluebot/scripts/renew-ssl.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SSL_DIR="${BASE_DIR}/data/ssl"
CERTBOT_WWW="${BASE_DIR}/certbot/www"
EMAIL="admin@bluebotapp.com.br"

DOMAINS=(
    "bluebotapp.com.br"
    "www.bluebotapp.com.br"
    "api.bluebotapp.com.br"
    "console.bluebotapp.com.br"
    "app.bluebotapp.com.br"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }

mkdir -p "${SSL_DIR}" "${CERTBOT_WWW}"

# ─── Renovar certificados existentes ─────────────────────────────────────
renew() {
    log_info "Renovando certificados existentes via Certbot container..."

    if docker inspect bluebot_certbot &>/dev/null; then
        docker exec bluebot_certbot certbot renew \
            --webroot -w /var/www/certbot \
            --quiet \
            --deploy-hook "echo 'Cert renewed'"
        log_ok "Renovação concluída!"
    else
        log_warn "Container certbot não encontrado. Usando standalone..."
        generate_new
    fi

    # Reload nginx para usar certs novos
    if docker inspect bluebot_nginx &>/dev/null; then
        docker exec bluebot_nginx nginx -s reload
        log_ok "Nginx recarregado com novos certificados"
    fi
}

# ─── Gerar novos certificados ────────────────────────────────────────────
generate_new() {
    log_info "Gerando novos certificados via standalone..."
    log_warn "O Nginx será parado temporariamente (porta 80 necessária)"

    # Construir lista de -d flags
    DOMAIN_FLAGS=""
    for d in "${DOMAINS[@]}"; do
        DOMAIN_FLAGS="${DOMAIN_FLAGS} -d ${d}"
    done

    # Parar nginx temporariamente
    docker stop bluebot_nginx 2>/dev/null || true

    # Rodar certbot standalone
    docker run --rm \
        -p 80:80 \
        -v "${SSL_DIR}:/etc/letsencrypt" \
        certbot/certbot certonly \
        --standalone \
        ${DOMAIN_FLAGS} \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        --force-renewal

    # Reiniciar nginx
    docker start bluebot_nginx 2>/dev/null || true

    log_ok "Certificados gerados com sucesso!"

    # Verificar resultado
    log_info "Verificando certificado..."
    if [ -f "${SSL_DIR}/live/bluebotapp.com.br/fullchain.pem" ]; then
        openssl x509 -in "${SSL_DIR}/live/bluebotapp.com.br/fullchain.pem" \
            -noout -dates -subject 2>/dev/null
        log_ok "Certificado válido!"
    else
        log_err "Certificado não encontrado após geração!"
        exit 1
    fi
}

# ─── Main ────────────────────────────────────────────────────────────────
case "${1:-}" in
    --new)
        generate_new
        ;;
    *)
        renew
        ;;
esac
