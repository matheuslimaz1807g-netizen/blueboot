#!/bin/bash
# =============================================================================
# scripts/remover-cliente.sh
# Remove um cliente BlueBot de forma segura e com confirmações.
#
# Uso:
#   bash scripts/remover-cliente.sh <slug>
#   Ex: bash scripts/remover-cliente.sh empresa-abc
#
# O que este script faz:
#   1. Valida que o slug existe
#   2. Pede confirmação
#   3. Para e remove os containers
#   4. Pergunta se quer apagar os volumes (sessões WhatsApp e dados do bot)
#   5. Remove a pasta do cliente
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CLIENTES_DIR="${BASE_DIR}/clientes"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ---------------------------------------------------------------------------
# 1. Validar argumento
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
  log_error "Uso: $0 <slug>"
  log_error "Exemplo: $0 empresa-abc"
  exit 1
fi

SLUG="${1}"
CLIENTE_DIR="${CLIENTES_DIR}/${SLUG}"

# ---------------------------------------------------------------------------
# 2. Verificar se o cliente existe
# ---------------------------------------------------------------------------
if [[ ! -d "${CLIENTE_DIR}" ]]; then
  log_error "Cliente '${SLUG}' não encontrado em ${CLIENTE_DIR}"
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Pedir confirmação — dois passos para evitar remoção acidental
# ---------------------------------------------------------------------------
echo ""
echo -e "${RED}════════════════════════════════════════${NC}"
echo -e "${RED}  ATENÇÃO: Remoção de cliente${NC}"
echo -e "${RED}════════════════════════════════════════${NC}"
echo ""
echo -e "  Cliente: ${YELLOW}${SLUG}${NC}"
echo -e "  Pasta:   ${YELLOW}${CLIENTE_DIR}${NC}"
echo ""
log_warn "Esta ação irá PARAR e REMOVER os containers do cliente '${SLUG}'."
echo ""
read -rp "  Digite o slug '${SLUG}' para confirmar a remoção: " CONFIRM

if [[ "${CONFIRM}" != "${SLUG}" ]]; then
  log_info "Remoção cancelada."
  exit 0
fi

# ---------------------------------------------------------------------------
# 4. Parar e remover os containers
# ---------------------------------------------------------------------------
log_info "Parando containers do cliente '${SLUG}'..."
cd "${CLIENTE_DIR}"

if docker compose ps --quiet 2>/dev/null | grep -q .; then
  docker compose down
  log_ok "Containers parados e removidos."
else
  log_warn "Nenhum container em execução encontrado. Continuando..."
fi

# ---------------------------------------------------------------------------
# 5. Perguntar sobre volumes (sessão WhatsApp + dados do bot)
# ---------------------------------------------------------------------------
echo ""
log_warn "Os volumes abaixo contêm a sessão WhatsApp e dados do bot do cliente:"
echo ""
echo -e "  - whatsapp_auth_${SLUG}   (sessão de autenticação WhatsApp)"
echo -e "  - whatsapp_cache_${SLUG}  (cache do Chromium)"
echo -e "  - bot_sessions_${SLUG}    (sessão Telegram)"
echo -e "  - bot_data_${SLUG}        (dados e cache de links)"
echo ""
log_warn "SE APAGAR: o cliente terá que escanear o QR code novamente."
echo ""
read -rp "  Deseja APAGAR os volumes? (s/N): " DEL_VOLUMES

if [[ "${DEL_VOLUMES,,}" == "s" ]]; then
  log_info "Removendo volumes..."

  VOLUMES=(
    "whatsapp_auth_${SLUG}"
    "whatsapp_cache_${SLUG}"
    "bot_sessions_${SLUG}"
    "bot_data_${SLUG}"
  )

  for VOL in "${VOLUMES[@]}"; do
    # O nome real do volume no Docker inclui o nome do projeto (pasta do compose)
    FULL_VOL_NAME="${SLUG}_${VOL}"
    if docker volume inspect "${FULL_VOL_NAME}" &>/dev/null; then
      docker volume rm "${FULL_VOL_NAME}"
      log_ok "Volume removido: ${FULL_VOL_NAME}"
    else
      log_warn "Volume não encontrado (pode já ter sido removido): ${FULL_VOL_NAME}"
    fi
  done
else
  log_info "Volumes preservados. Para removê-los manualmente:"
  echo "  docker volume rm ${SLUG}_whatsapp_auth_${SLUG} ${SLUG}_whatsapp_cache_${SLUG} ${SLUG}_bot_sessions_${SLUG} ${SLUG}_bot_data_${SLUG}"
fi

# ---------------------------------------------------------------------------
# 6. Remover a pasta do cliente
# ---------------------------------------------------------------------------
echo ""
read -rp "  Remover a pasta ${CLIENTE_DIR}? (s/N): " DEL_FOLDER

if [[ "${DEL_FOLDER,,}" == "s" ]]; then
  # Último backup do .env antes de apagar (para recuperação de emergência)
  BACKUP_FILE="/tmp/bluebot_${SLUG}_env_backup_$(date +%Y%m%d%H%M%S).txt"
  if [[ -f "${CLIENTE_DIR}/.env" ]]; then
    cp "${CLIENTE_DIR}/.env" "${BACKUP_FILE}"
    chmod 600 "${BACKUP_FILE}"
    log_warn "Backup do .env salvo em ${BACKUP_FILE} (remova manualmente após confirmar)"
  fi

  rm -rf "${CLIENTE_DIR}"
  log_ok "Pasta removida: ${CLIENTE_DIR}"
else
  log_info "Pasta preservada: ${CLIENTE_DIR}"
fi

# ---------------------------------------------------------------------------
# 7. Confirmação final
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  Cliente '${SLUG}' removido com sucesso!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
log_info "Nota: A licença do cliente ainda existe no banco de dados."
log_info "Para desativar a licença, acesse o painel admin → Licenças."
echo ""
