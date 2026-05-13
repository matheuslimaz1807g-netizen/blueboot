#!/bin/bash
# =============================================================================
# scripts/novo-cliente.sh
# Provisiona um novo cliente BlueBot de forma segura e interativa.
#
# Uso:
#   bash scripts/novo-cliente.sh <slug>
#   Ex: bash scripts/novo-cliente.sh empresa-abc
#
# Requisitos:
#   - Executar na VPS como root ou usuário com acesso ao Docker
#   - O core (postgres + api + nginx) deve estar UP antes de usar este script
#   - A pasta /opt/bluebot/clientes/template deve existir
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Constantes e caminhos
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CLIENTES_DIR="${BASE_DIR}/clientes"
TEMPLATE_DIR="${CLIENTES_DIR}/template"
DOMAIN="bluebotapp.com.br"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ---------------------------------------------------------------------------
# 1. Validar argumento
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
  log_error "Uso: $0 <slug>"
  log_error "Exemplo: $0 empresa-abc"
  exit 1
fi

SLUG="${1}"

# Validar formato do slug: apenas letras minúsculas, números e hífens
if ! [[ "${SLUG}" =~ ^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$ ]]; then
  log_error "Slug inválido: '${SLUG}'"
  log_error "Use apenas letras minúsculas, números e hífens (3-30 chars, sem começar/terminar com hífen)."
  exit 1
fi

CLIENTE_DIR="${CLIENTES_DIR}/${SLUG}"

# ---------------------------------------------------------------------------
# 2. Verificar se cliente já existe
# ---------------------------------------------------------------------------
if [[ -d "${CLIENTE_DIR}" ]]; then
  log_error "Cliente '${SLUG}' já existe em ${CLIENTE_DIR}"
  log_error "Para recriar, remova primeiro com: bash scripts/remover-cliente.sh ${SLUG}"
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Verificar dependências
# ---------------------------------------------------------------------------
for cmd in docker sed awk; do
  if ! command -v "${cmd}" &>/dev/null; then
    log_error "Comando '${cmd}' não encontrado. Instale e tente novamente."
    exit 1
  fi
done

if [[ ! -d "${TEMPLATE_DIR}" ]]; then
  log_error "Pasta de template não encontrada: ${TEMPLATE_DIR}"
  exit 1
fi

# ---------------------------------------------------------------------------
# 4. Coletar variáveis obrigatórias interativamente
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo -e "${CYAN}  BlueBot — Novo Cliente: ${SLUG}${NC}"
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo ""
log_info "Preencha as informações abaixo. Campos em branco usarão o padrão."
echo ""

prompt_required() {
  local var_name="$1"
  local prompt_text="$2"
  local value=""
  while [[ -z "${value}" ]]; do
    read -rp "  ${prompt_text}: " value
    if [[ -z "${value}" ]]; then
      log_warn "Este campo é obrigatório."
    fi
  done
  echo "${value}"
}

prompt_optional() {
  local prompt_text="$1"
  local default_val="$2"
  local value=""
  read -rp "  ${prompt_text} [${default_val}]: " value
  echo "${value:-${default_val}}"
}

prompt_secret() {
  local var_name="$1"
  local prompt_text="$2"
  local value=""
  while [[ -z "${value}" ]]; do
    read -rsp "  ${prompt_text}: " value
    echo ""
    if [[ -z "${value}" ]]; then
      log_warn "Este campo é obrigatório."
    fi
  done
  echo "${value}"
}

LICENSE_KEY=$(prompt_required "LICENSE_KEY" "Chave de licença (APRO-XXXX-XXXX-XXXX)")
CLIENT_PASSWORD=$(prompt_secret "CLIENT_PASSWORD" "Senha do cliente no painel admin")
TELEGRAM_API_ID=$(prompt_required "TELEGRAM_API_ID" "Telegram API ID (my.telegram.org)")
TELEGRAM_API_HASH=$(prompt_secret "TELEGRAM_API_HASH" "Telegram API Hash")
TELEGRAM_PHONE=$(prompt_required "TELEGRAM_PHONE" "Telefone Telegram (+5511999999999)")
TELEGRAM_SOURCES=$(prompt_required "TELEGRAM_SOURCES" "Canais de origem (username1,username2)")
TELEGRAM_DESTINATION=$(prompt_required "TELEGRAM_DESTINATION" "Destino Telegram (username ou ID)")
BOT_DELAY=$(prompt_optional "Delay entre mensagens em segundos" "3")

echo ""
log_info "Credenciais de afiliados (pressione Enter para deixar em branco):"
SHOPEE_TOKEN=$(prompt_optional "Shopee Token" "")
ALI_KEY=$(prompt_optional "AliExpress Key" "")
ALI_SECRET=$(prompt_optional "AliExpress Secret" "")
ALI_TRACKING=$(prompt_optional "AliExpress Tracking ID" "")
ML_TOKEN=$(prompt_optional "Mercado Livre Token" "")

# ---------------------------------------------------------------------------
# 5. Copiar template e substituir CLIENTE_SLUG
# ---------------------------------------------------------------------------
log_info "Criando diretório do cliente..."
mkdir -p "${CLIENTE_DIR}"

# Copia o docker-compose.yml do template e substitui o slug
sed "s/\${CLIENTE_SLUG}/${SLUG}/g" \
  "${TEMPLATE_DIR}/docker-compose.yml" \
  > "${CLIENTE_DIR}/docker-compose.yml"

log_ok "docker-compose.yml criado para '${SLUG}'"

# ---------------------------------------------------------------------------
# 6. Criar .env a partir do .env.example com as variáveis coletadas
# ---------------------------------------------------------------------------
log_info "Criando arquivo .env..."

cat > "${CLIENTE_DIR}/.env" << EOF
# =============================================================================
# BlueBot — Cliente: ${SLUG}
# Gerado automaticamente por novo-cliente.sh em $(date '+%Y-%m-%d %H:%M:%S')
# NUNCA compartilhe ou faça commit deste arquivo.
# =============================================================================

CLIENTE_SLUG=${SLUG}

# Autenticação na API Central
LICENSE_KEY=${LICENSE_KEY}
CLIENT_PASSWORD=${CLIENT_PASSWORD}
DASHBOARD_PASSWORD=${CLIENT_PASSWORD}
APRO_API_BASE=http://bluebot_api:8000

# Telegram
TELEGRAM_API_ID=${TELEGRAM_API_ID}
TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
TELEGRAM_PHONE=${TELEGRAM_PHONE}
TELEGRAM_SESSION_STRING=
TELEGRAM_SOURCES=${TELEGRAM_SOURCES}
TELEGRAM_DESTINATION=${TELEGRAM_DESTINATION}
BOT_DELAY_SEGUNDOS=${BOT_DELAY}

# WhatsApp (endpoint interno via rede Docker)
WHATSAPP_ENDPOINT=http://whatsapp_${SLUG}:4000

# Afiliados
SHOPEE_TOKEN=${SHOPEE_TOKEN}
ALI_KEY=${ALI_KEY}
ALI_SECRET=${ALI_SECRET}
ALI_TRACKING=${ALI_TRACKING}
ML_TOKEN=${ML_TOKEN}

# Runtime
DOCKER_CONTAINER=1
EOF

# Restringir permissões do .env (apenas root lê)
chmod 600 "${CLIENTE_DIR}/.env"
log_ok ".env criado e protegido (chmod 600)"

# ---------------------------------------------------------------------------
# 7. Subir os containers
# ---------------------------------------------------------------------------
log_info "Subindo containers do cliente '${SLUG}'..."
cd "${CLIENTE_DIR}"
docker compose up -d

# ---------------------------------------------------------------------------
# 8. Verificar se subiram corretamente
# ---------------------------------------------------------------------------
echo ""
log_info "Status dos containers:"
docker compose ps

# Aguarda até 60s pelo healthcheck do whatsapp (demora para autenticar)
log_info "Aguardando containers ficarem saudáveis (pode levar até 90s)..."
TIMEOUT=90
ELAPSED=0
while [[ ${ELAPSED} -lt ${TIMEOUT} ]]; do
  WA_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "whatsapp_${SLUG}" 2>/dev/null || echo "unknown")
  BOT_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "bot_${SLUG}" 2>/dev/null || echo "unknown")

  if [[ "${WA_STATUS}" == "healthy" ]] && [[ "${BOT_STATUS}" == "healthy" ]]; then
    log_ok "Todos os containers estão saudáveis!"
    break
  fi

  echo -ne "  WhatsApp: ${WA_STATUS} | Bot: ${BOT_STATUS} (${ELAPSED}s)...\r"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

echo ""

if [[ "${WA_STATUS}" != "healthy" ]] || [[ "${BOT_STATUS}" != "healthy" ]]; then
  log_warn "Containers ainda não estão healthy após ${TIMEOUT}s."
  log_warn "Verifique os logs: docker compose -f ${CLIENTE_DIR}/docker-compose.yml logs -f"
  log_warn "O WhatsApp pode precisar de scan do QR code — acesse o painel admin."
fi

# ---------------------------------------------------------------------------
# 9. Exibir URL de acesso e próximos passos
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  Cliente '${SLUG}' provisionado!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "  🌐 Dashboard: ${CYAN}https://${SLUG}.${DOMAIN}${NC}"
echo -e "  📁 Arquivos:  ${CYAN}${CLIENTE_DIR}${NC}"
echo ""
echo -e "  Próximos passos:"
echo -e "  1. Acesse o painel admin → Licenças → '${SLUG}'"
echo -e "  2. Escaneie o QR code do WhatsApp se ainda não foi feito"
echo -e "  3. Configure DNS wildcard para *.${DOMAIN} se necessário"
echo ""
