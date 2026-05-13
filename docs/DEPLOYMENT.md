# 🚢 Deploy — Atualizar o Sistema

## Deploy de Atualizações (Sem Downtime)

### Passo a passo:

```bash
# 1. Conectar na VPS
ssh root@SEU_IP
cd /opt/bluebot

# 2. SEMPRE fazer backup antes
bash scripts/backup-postgres.sh

# 3. Baixar código novo do GitHub
git pull

# 4. Reconstruir a API (se mudou código Python)
docker compose build api

# 5. Aplicar mudanças
docker compose up -d

# 6. Verificar se tudo subiu
bash scripts/health-check.sh
```

> 💡 O `docker compose up -d` só reinicia containers que mudaram. Os outros continuam rodando (zero downtime).

---

## Se algo deu errado (Rollback)

### Opção 1: Voltar o código

```bash
# Ver os últimos commits
git log --oneline -5

# Voltar para um commit específico
git checkout HASH_DO_COMMIT -- .

# Rebuild e aplicar
docker compose build api
docker compose up -d
```

### Opção 2: Restaurar banco de dados

```bash
# Listar backups
ls -lh data/backups/postgres/

# Restaurar
gunzip < data/backups/postgres/bluebot_20260512_030000.sql.gz | \
  docker compose exec -T postgres psql -U bluebot bluebot
```

### Opção 3: Voltar tudo (último recurso)

```bash
# Se tiver o backup completo do tar:
# 1. Parar tudo
docker compose down
# 2. Restaurar arquivos
tar -xzf /tmp/bluebot-backup-XXXXXX.tar.gz -C /opt/
# 3. Subir novamente
docker compose up -d
```

---

## Atualizar Apenas o Nginx (após mudar configs)

```bash
# Testar config antes de aplicar
docker compose exec nginx nginx -t

# Se OK, reiniciar apenas o nginx
docker compose restart nginx

# Se NOK, ver o erro e corrigir o arquivo indicado
```

---

## Checklist Pré-Deploy

- [ ] Backup do banco: `bash scripts/backup-postgres.sh`
- [ ] `git pull` sem conflitos
- [ ] `docker compose build` sem erros
- [ ] `docker compose up -d` sem erros
- [ ] `bash scripts/health-check.sh` passando
- [ ] Testar login no painel admin
- [ ] Testar login no painel do cliente
