#!/usr/bin/env bash
# =============================================================================
# sync-bot-secrets.sh — Expõe INSTALL_TOKEN da API central aos bots dos clientes
# =============================================================================
# Uso (na VPS, raiz do projeto):
#   ./scripts/sync-bot-secrets.sh
#
# Gera: /opt/bluebot/shared/bot-secrets.env  (só INSTALL_TOKEN)
# Os docker-compose dos clientes montam esse arquivo — sem LICENSE_KEY no .env.
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CENTRAL_ENV="${ROOT_DIR}/.env"
SHARED_DIR="${ROOT_DIR}/shared"
OUT_FILE="${SHARED_DIR}/bot-secrets.env"

if [[ ! -f "${CENTRAL_ENV}" ]]; then
  echo "❌ Arquivo não encontrado: ${CENTRAL_ENV}"
  echo "   Copie .env.example → .env e defina INSTALL_TOKEN."
  exit 1
fi

# Extrai INSTALL_TOKEN do .env central (ignora comentários e espaços)
TOKEN="$(
  grep -E '^[[:space:]]*INSTALL_TOKEN=' "${CENTRAL_ENV}" \
    | tail -n1 \
    | cut -d= -f2- \
    | sed 's/^[[:space:]]*//;s/[[:space:]]*$//;s/^"//;s/"$//;s/^'"'"'//;s/'"'"'$//'
)"

if [[ -z "${TOKEN}" || "${TOKEN}" == CHANGE_ME* ]]; then
  echo "❌ INSTALL_TOKEN vazio ou placeholder em ${CENTRAL_ENV}"
  echo "   Gere um: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
  exit 1
fi

mkdir -p "${SHARED_DIR}"
cat > "${OUT_FILE}" << EOF
# Gerado por scripts/sync-bot-secrets.sh — NÃO edite na mão
# Fonte: ${CENTRAL_ENV}
INSTALL_TOKEN=${TOKEN}
EOF
chmod 600 "${OUT_FILE}"

echo "✅ Gerado: ${OUT_FILE}"
echo "   Recrie os bots para aplicar:"
echo "   cd clientes/<slug> && docker compose up -d --force-recreate bot_<slug>"
