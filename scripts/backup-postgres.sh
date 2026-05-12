#!/bin/bash
# =============================================================================
# scripts/backup-postgres.sh — Backup automático do PostgreSQL
#
# Uso:
#   bash scripts/backup-postgres.sh
#   crontab: 0 3 * * * /opt/bluebot/scripts/backup-postgres.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BASE_DIR}/data/backups/postgres"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/bluebot_${TIMESTAMP}.sql.gz"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC}    $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Criar diretório de backup
mkdir -p "${BACKUP_DIR}"

# Verificar se o container do postgres está rodando
if ! docker inspect bluebot_postgres &>/dev/null; then
    log_err "Container bluebot_postgres não encontrado!"
    exit 1
fi

# Extrair credenciais do .env
if [ -f "${BASE_DIR}/.env" ]; then
    POSTGRES_USER=$(grep -E "^POSTGRES_USER=" "${BASE_DIR}/.env" | cut -d= -f2)
    POSTGRES_DB=$(grep -E "^POSTGRES_DB=" "${BASE_DIR}/.env" | cut -d= -f2)
else
    POSTGRES_USER="bluebot"
    POSTGRES_DB="bluebot"
fi

log_info "Iniciando backup do PostgreSQL..."
log_info "Database: ${POSTGRES_DB} | User: ${POSTGRES_USER}"

# Executar pg_dump dentro do container
if docker exec bluebot_postgres pg_dump \
    -U "${POSTGRES_USER}" \
    "${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    2>/dev/null | gzip > "${BACKUP_FILE}"; then

    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log_ok "Backup salvo: ${BACKUP_FILE} (${SIZE})"
else
    log_err "Falha ao criar backup!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Limpar backups antigos
DELETED=$(find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [ "${DELETED}" -gt 0 ]; then
    log_info "Removidos ${DELETED} backup(s) com mais de ${RETENTION_DAYS} dias"
fi

# Listar backups existentes
log_info "Backups disponíveis:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'

echo ""
log_ok "Backup concluído com sucesso!"
