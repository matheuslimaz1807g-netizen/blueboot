# BlueBot — Deploy e Manutenção

## Deploy Inicial

### 1. Configurar VPS
```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
# Criar diretório
mkdir -p /opt/bluebot
cd /opt/bluebot
# Clonar repositório
git clone <repo-url> .
```

### 2. Configurar ambiente
```bash
cp .env.example .env
nano .env  # Preencher TODAS as variáveis
```

### 3. Criar rede e estrutura
```bash
docker network create bluebot_network
mkdir -p data/{ssl,backups/postgres} certbot/www
```

### 4. Gerar certificados SSL
```bash
bash scripts/renew-ssl.sh --new
```

### 5. Subir infraestrutura
```bash
docker compose up -d
bash scripts/health-check.sh
```

## Migração de /usr/blueboot → /opt/bluebot

```bash
cd /usr/blueboot
git pull  # Pegar mudanças da reestruturação
sudo bash scripts/migrate.sh
```

## Atualizar Código

```bash
cd /opt/bluebot
git pull
docker compose build api  # Rebuild da API
docker compose up -d      # Aplicar
```

## Crontab Recomendado

```bash
crontab -e
# Adicionar:
0 3 * * * /opt/bluebot/scripts/backup-postgres.sh
0 4 * * 1 /opt/bluebot/scripts/renew-ssl.sh
*/5 * * * * /opt/bluebot/scripts/health-check.sh --quiet
```

## Restaurar Backup do Postgres

```bash
gunzip < data/backups/postgres/bluebot_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i bluebot_postgres psql -U bluebot bluebot
```
