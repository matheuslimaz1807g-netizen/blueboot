#!/bin/bash
# =============================================================================
# scripts/migrate.sh — Migrar de /usr/blueboot → /opt/bluebot
#
# Este script:
#   1. Faz backup completo da estrutura atual
#   2. Cria a nova estrutura em /opt/bluebot
#   3. Move os dados
#   4. Cria symlink de compatibilidade
#   5. Recria containers com nova estrutura
#
# Uso na VPS (como root):
#   chmod +x scripts/migrate.sh && bash scripts/migrate.sh
# =============================================================================

set -euo pipefail

OLD_DIR="/usr/blueboot"
NEW_DIR="/opt/bluebot"
BACKUP_FILE="/tmp/bluebot-pre-migration-$(date +%Y%m%d_%H%M%S).tar.gz"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_err()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  BlueBot — Migração ${OLD_DIR} → ${NEW_DIR}${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

# ─── Verificações ────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    log_err "Execute como root: sudo bash scripts/migrate.sh"
    exit 1
fi

if [ ! -d "${OLD_DIR}" ]; then
    log_err "Diretório ${OLD_DIR} não encontrado!"
    exit 1
fi

if [ -d "${NEW_DIR}" ] && [ "$(ls -A ${NEW_DIR} 2>/dev/null)" ]; then
    log_err "${NEW_DIR} já existe e não está vazio!"
    log_err "Remova ou renomeie antes de migrar."
    exit 1
fi

# ─── Etapa 1: Backup ────────────────────────────────────────────────────
log_info "Etapa 1/6: Backup completo..."

# Backup do banco de dados
if docker inspect bluebot_postgres &>/dev/null; then
    PG_USER=$(grep -E "^POSTGRES_USER=" "${OLD_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "bluebot")
    PG_DB=$(grep -E "^POSTGRES_DB=" "${OLD_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo "bluebot")
    docker exec bluebot_postgres pg_dump -U "${PG_USER}" "${PG_DB}" > "/tmp/bluebot-pg-premigration.sql"
    log_ok "Backup do Postgres: /tmp/bluebot-pg-premigration.sql"
fi

# Backup dos arquivos
tar -czf "${BACKUP_FILE}" -C "$(dirname ${OLD_DIR})" "$(basename ${OLD_DIR})" 2>/dev/null
log_ok "Backup dos arquivos: ${BACKUP_FILE}"

# ─── Etapa 2: Criar nova estrutura ──────────────────────────────────────
log_info "Etapa 2/6: Criando nova estrutura..."

mkdir -p "${NEW_DIR}"/{data/{ssl,backups/postgres},certbot/www,logs/{nginx,api}}

log_ok "Estrutura de diretórios criada"

# ─── Etapa 3: Copiar código ─────────────────────────────────────────────
log_info "Etapa 3/6: Copiando código..."

# Copiar tudo exceto dados voláteis
rsync -a --progress \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude 'ssl' \
    --exclude '*.log' \
    "${OLD_DIR}/" "${NEW_DIR}/"

log_ok "Código copiado"

# ─── Etapa 4: Migrar certificados SSL ───────────────────────────────────
log_info "Etapa 4/6: Migrando certificados SSL..."

# Procurar certs no local antigo
SSL_FOUND=""
for ssl_path in "${OLD_DIR}/ssl/letsencrypt" "${OLD_DIR}/ssl" "${OLD_DIR}/data/ssl"; do
    if [ -d "${ssl_path}/live/bluebotapp.com.br" ]; then
        SSL_FOUND="${ssl_path}"
        break
    fi
done

if [ -n "${SSL_FOUND}" ]; then
    cp -a "${SSL_FOUND}/." "${NEW_DIR}/data/ssl/"
    log_ok "Certificados copiados de ${SSL_FOUND} → ${NEW_DIR}/data/ssl/"
else
    log_warn "Certificados não encontrados — será necessário regenerar"
    log_warn "Execute: bash scripts/renew-ssl.sh --new"
fi

# ─── Etapa 5: Criar symlink de compatibilidade ──────────────────────────
log_info "Etapa 5/6: Criando symlink de compatibilidade..."

# Parar containers atuais
log_info "Parando containers..."
cd "${OLD_DIR}"
docker compose down 2>/dev/null || true

# Parar containers de clientes
for client_dir in "${OLD_DIR}/clientes"/*/; do
    if [ -f "${client_dir}/docker-compose.yml" ]; then
        cd "${client_dir}"
        docker compose down 2>/dev/null || true
    fi
done

# Renomear antigo e criar symlink
mv "${OLD_DIR}" "${OLD_DIR}.bak"
ln -s "${NEW_DIR}" "${OLD_DIR}"
log_ok "Symlink criado: ${OLD_DIR} → ${NEW_DIR}"

# ─── Etapa 6: Subir containers com nova estrutura ───────────────────────
log_info "Etapa 6/6: Subindo containers..."

cd "${NEW_DIR}"

# Garantir rede
docker network create bluebot_network 2>/dev/null || true

# Subir infra
docker compose up -d
log_ok "Infraestrutura iniciada"

# Subir clientes
for client_dir in "${NEW_DIR}/clientes"/*/; do
    if [ -f "${client_dir}/docker-compose.yml" ] && [ "$(basename ${client_dir})" != "template" ]; then
        cd "${client_dir}"
        docker compose up -d
        log_ok "Cliente $(basename ${client_dir}) iniciado"
    fi
done

# ─── Resumo ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Migração concluída!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  📂 Novo local:    ${CYAN}${NEW_DIR}${NC}"
echo -e "  🔗 Symlink:       ${CYAN}${OLD_DIR} → ${NEW_DIR}${NC}"
echo -e "  💾 Backup:        ${CYAN}${BACKUP_FILE}${NC}"
echo -e "  🗄️  Backup DB:     ${CYAN}/tmp/bluebot-pg-premigration.sql${NC}"
echo ""
echo -e "  Próximos passos:"
echo -e "  1. Verificar: ${CYAN}bash scripts/health-check.sh${NC}"
echo -e "  2. Se OK, remover backup: ${CYAN}rm -rf ${OLD_DIR}.bak${NC}"
echo -e "  3. Configurar crontab:"
echo -e "     ${CYAN}0 3 * * * ${NEW_DIR}/scripts/backup-postgres.sh${NC}"
echo -e "     ${CYAN}0 4 * * 1 ${NEW_DIR}/scripts/renew-ssl.sh${NC}"
echo ""
