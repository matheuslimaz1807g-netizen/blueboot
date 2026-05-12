#!/bin/bash
# =============================================================================
# scripts/health-check.sh — Verificar saúde de todos os serviços
#
# Uso:
#   bash scripts/health-check.sh
#   crontab: */5 * * * * /opt/bluebot/scripts/health-check.sh --quiet
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

QUIET="${1:-}"
ERRORS=0

log_info() { [[ "$QUIET" != "--quiet" ]] && echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()   { [[ "$QUIET" != "--quiet" ]] && echo -e "${GREEN}  ✅${NC} $1"; }
log_warn() { echo -e "${YELLOW}  ⚠️${NC}  $1"; }
log_fail() { echo -e "${RED}  ❌${NC} $1"; ERRORS=$((ERRORS + 1)); }

echo ""
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}  BlueBot — Health Check${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo ""

# ─── 1. Containers ───────────────────────────────────────────────────────
log_info "Verificando containers..."

CONTAINERS=("bluebot_postgres" "bluebot_api" "bluebot_nginx" "bluebot_certbot")
for c in "${CONTAINERS[@]}"; do
    STATUS=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "not_found")
    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$c" 2>/dev/null || echo "unknown")

    if [[ "$STATUS" == "running" ]]; then
        if [[ "$HEALTH" == "healthy" || "$HEALTH" == "no_healthcheck" ]]; then
            log_ok "$c: running ($HEALTH)"
        else
            log_warn "$c: running ($HEALTH)"
        fi
    else
        log_fail "$c: $STATUS"
    fi
done

# ─── 2. API ──────────────────────────────────────────────────────────────
echo ""
log_info "Verificando API..."

API_STATUS=$(curl -sf --connect-timeout 5 http://localhost:8000/health 2>/dev/null || echo "FAIL")
if echo "$API_STATUS" | grep -q "ok"; then
    log_ok "API /health: OK"
else
    log_fail "API /health: FALHOU"
fi

# ─── 3. HTTPS ────────────────────────────────────────────────────────────
echo ""
log_info "Verificando HTTPS..."

DOMAINS=("bluebotapp.com.br" "console.bluebotapp.com.br" "api.bluebotapp.com.br" "app.bluebotapp.com.br")
for d in "${DOMAINS[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://$d/" 2>/dev/null || echo "000")
    case "$HTTP_CODE" in
        200|301|302) log_ok "https://$d → $HTTP_CODE" ;;
        000)         log_fail "https://$d → conexão falhou" ;;
        *)           log_warn "https://$d → $HTTP_CODE" ;;
    esac
done

# ─── 4. SSL Certificate ─────────────────────────────────────────────────
echo ""
log_info "Verificando certificado SSL..."

CERT_INFO=$(echo | openssl s_client -connect localhost:443 -servername bluebotapp.com.br 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null || echo "FAIL")
if [[ "$CERT_INFO" != "FAIL" ]]; then
    EXPIRY_DATE=$(echo "$CERT_INFO" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    if [[ $DAYS_LEFT -gt 30 ]]; then
        log_ok "Certificado válido por mais $DAYS_LEFT dias"
    elif [[ $DAYS_LEFT -gt 7 ]]; then
        log_warn "Certificado expira em $DAYS_LEFT dias — renovar em breve!"
    else
        log_fail "Certificado expira em $DAYS_LEFT dias — RENOVAR AGORA!"
    fi
else
    log_fail "Não foi possível verificar o certificado"
fi

# ─── 5. Disco ────────────────────────────────────────────────────────────
echo ""
log_info "Verificando disco..."

DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [[ $DISK_USAGE -lt 80 ]]; then
    log_ok "Uso de disco: ${DISK_USAGE}%"
elif [[ $DISK_USAGE -lt 90 ]]; then
    log_warn "Uso de disco: ${DISK_USAGE}% — limpar espaço!"
else
    log_fail "Uso de disco: ${DISK_USAGE}% — CRÍTICO!"
fi

# ─── 6. Clientes ─────────────────────────────────────────────────────────
echo ""
log_info "Verificando containers de clientes..."

CLIENT_CONTAINERS=$(docker ps --filter "name=whatsapp_" --filter "name=bot_" --format "{{.Names}}: {{.Status}}" 2>/dev/null || echo "")
if [[ -n "$CLIENT_CONTAINERS" ]]; then
    while IFS= read -r line; do
        if echo "$line" | grep -q "Up"; then
            log_ok "$line"
        else
            log_warn "$line"
        fi
    done <<< "$CLIENT_CONTAINERS"
else
    log_warn "Nenhum container de cliente encontrado"
fi

# ─── Resumo ──────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}  ✅ Todos os serviços estão saudáveis!${NC}"
else
    echo -e "${RED}  ❌ ${ERRORS} problema(s) encontrado(s)!${NC}"
fi
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo ""

exit $ERRORS
