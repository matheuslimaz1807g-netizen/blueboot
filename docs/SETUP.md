# 🔧 Setup — Instalação do Zero

## Requisitos Mínimos da VPS

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

---

## Passo 1: Instalar Docker

```bash
# Conectar na VPS
ssh root@SEU_IP

# Instalar Docker (script oficial)
curl -fsSL https://get.docker.com | sh

# Verificar instalação
docker --version      # Deve mostrar: Docker version 24.x
docker compose version  # Deve mostrar: Docker Compose version v2.x
```

> 💡 **O que é Docker?** Veja [GETTING-STARTED.md](GETTING-STARTED.md) para uma explicação simples.

---

## Passo 2: Clonar o Repositório

```bash
# Instalar Git (se não tiver)
apt update && apt install -y git

# Clonar o projeto
cd /opt
git clone https://github.com/SEU_USUARIO/blueboot.git bluebot
cd /opt/bluebot
```

---

## Passo 3: Configurar o .env

```bash
# Copiar o template
cp .env.example .env

# Editar com nano (editor de texto no terminal)
nano .env
```

### Cada variável explicada:

```bash
# ── Database ──────────────────────────────────────────
# Nome do usuário no PostgreSQL (pode manter "bluebot")
POSTGRES_USER=bluebot

# Senha do banco de dados (gere uma senha forte!)
# Como gerar: openssl rand -base64 32
POSTGRES_PASSWORD=SUA_SENHA_FORTE_AQUI

# Nome do banco de dados (pode manter "bluebot")
POSTGRES_DB=bluebot

# URL de conexão — substitua a senha pela mesma do POSTGRES_PASSWORD
# ⚠️ Se a senha tem caracteres especiais (!, @, #), codifique-os
DATABASE_URL=postgresql+asyncpg://bluebot:SUA_SENHA_FORTE_AQUI@postgres:5432/bluebot

# ── API Security ──────────────────────────────────────
# Chave secreta para gerar tokens JWT (login)
# Como gerar: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=COLE_AQUI_O_TOKEN_GERADO

# Chave para criptografia (protege dados sensíveis)
# Como gerar: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=COLE_AQUI_A_CHAVE
BLUEBOT_FERNET_KEY=COLE_AQUI_A_MESMA_CHAVE

# Token que os bots usam para se registrar na API
# Como gerar: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
INSTALL_TOKEN=COLE_AQUI_O_TOKEN

# ── Admin ─────────────────────────────────────────────
# Login e senha do painel admin (console.bluebotapp.com.br)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=SUA_SENHA_ADMIN

# ── Outras ────────────────────────────────────────────
RATE_LIMIT_PER_MINUTE=60
APP_VERSION=1.0.0
```

```bash
# Salvar no nano: Ctrl+O, Enter, Ctrl+X
```

> ⚠️ **NUNCA** compartilhe o arquivo `.env`! Ele contém todas as senhas do sistema.

---

## Passo 4: Criar Rede Docker e Diretórios

```bash
# Criar rede compartilhada entre containers
docker network create bluebot_network

# Criar diretórios de dados
mkdir -p data/{ssl,backups/postgres} certbot/www
```

---

## Passo 5: Gerar Certificados SSL

```bash
# Gerar certificados Let's Encrypt para todos os domínios
bash scripts/renew-ssl.sh --new
```

> ⚠️ Para isso funcionar, seus **domínios DNS devem apontar para o IP da VPS**.

---

## Passo 6: Configurar DNS

No painel da Hostinger (ou seu provedor DNS), adicione estes registros:

| Tipo | Nome | Valor | TTL |
|------|------|-------|-----|
| A | `@` | `SEU_IP_VPS` | 3600 |
| A | `www` | `SEU_IP_VPS` | 3600 |
| A | `api` | `SEU_IP_VPS` | 3600 |
| A | `console` | `SEU_IP_VPS` | 3600 |
| A | `app` | `SEU_IP_VPS` | 3600 |

Aguarde até 30 minutos para propagar.

### Verificar se propagou:

```bash
# Testar de qualquer lugar
dig +short api.bluebotapp.com.br
# Deve retornar: SEU_IP_VPS
```

---

## Passo 7: Subir os Containers

```bash
cd /opt/bluebot

# Subir tudo em segundo plano
docker compose up -d

# Verificar se subiram
docker compose ps

# Ver logs (se algo deu errado)
docker compose logs --tail 30
```

---

## Passo 8: Verificar

```bash
# Health check completo
bash scripts/health-check.sh

# Testar HTTPS manualmente
curl -I https://console.bluebotapp.com.br
# Deve retornar: HTTP/2 200

curl -I https://api.bluebotapp.com.br/health
# Deve retornar: {"status":"ok"}
```

---

## Passo 9: Configurar Crontab

```bash
# Agendar backup e renovação SSL automáticos
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/bluebot/scripts/backup-postgres.sh"; echo "0 4 * * 1 /opt/bluebot/scripts/renew-ssl.sh") | crontab -

# Verificar
crontab -l
```

---

## ✅ Checklist Final

- [ ] Docker instalado e funcionando
- [ ] Repositório clonado em `/opt/bluebot`
- [ ] `.env` configurado com senhas fortes
- [ ] Rede `bluebot_network` criada
- [ ] DNS apontando para a VPS
- [ ] Certificados SSL gerados
- [ ] Containers rodando (`docker compose ps`)
- [ ] Health check passando
- [ ] Crontab configurado
