# 🚀 Getting Started — Docker e Git para Iniciantes

## O que é Docker? (Explicação Simples)

Imagine que Docker é como uma **caixa de mudança**. Dentro de cada caixa (chamada **container**) você coloca tudo que um programa precisa para funcionar: o programa, as configurações e as dependências.

**Por que isso é bom?** Porque a caixa funciona igual em qualquer lugar — no seu computador, na VPS, em qualquer servidor. Sem aquele "na minha máquina funciona".

### Vocabulário Essencial

| Termo | O que é | Analogia |
|-------|---------|----------|
| **Imagem** | A "receita" do container | Receita de bolo |
| **Container** | Um programa rodando | O bolo pronto |
| **Volume** | Pasta para salvar dados permanentes | Gaveta do armário |
| **docker-compose.yml** | Arquivo que descreve todos os containers | Lista de compras |
| **Rede (network)** | Permite containers conversarem entre si | Interfone do prédio |

### Exemplo Real do BlueBotApp

```yaml
# docker-compose.yml (simplificado)
services:
  postgres:    # Container 1: banco de dados
  api:         # Container 2: FastAPI (backend)
  nginx:       # Container 3: proxy reverso (recebe as requisições da internet)
  certbot:     # Container 4: renova certificados SSL
```

Quando você roda `docker compose up -d`, o Docker:
1. Lê o `docker-compose.yml`
2. Cria cada container
3. Conecta todos na mesma rede (`bluebot_network`)
4. Inicia tudo em segundo plano (`-d` = detached)

---

## Comandos Essenciais

### 📋 Ver o que está rodando

```bash
# Ver containers ativos (como "Gerenciador de Tarefas")
docker compose ps

# Saída esperada:
# NAME              STATUS         PORTS
# bluebot_api       Up (healthy)   8000/tcp
# bluebot_nginx     Up             0.0.0.0:80->80, 0.0.0.0:443->443
# bluebot_postgres  Up (healthy)   5432/tcp
```

### 📜 Ver logs (mensagens do programa)

```bash
# Ver últimas 50 linhas de log de um serviço
docker compose logs api --tail 50

# Acompanhar logs em tempo real (como "tail -f")
# Pressione Ctrl+C para sair
docker compose logs api -f

# Ver logs de TODOS os serviços
docker compose logs --tail 20
```

### 🔄 Reiniciar serviços

```bash
# Reiniciar apenas o Nginx (por exemplo, após mudar configuração)
docker compose restart nginx

# Parar TUDO
docker compose down

# Subir TUDO novamente
docker compose up -d
```

### 🔍 Entrar dentro de um container

```bash
# Entrar no container da API (como SSH para dentro do container)
docker compose exec api sh

# Dentro do container, você pode:
#   - Ver arquivos: ls /app/
#   - Testar a API: curl localhost:8000/health
#   - Sair: exit

# Entrar no Postgres e fazer queries
docker compose exec postgres psql -U bluebot bluebot
# Dentro do psql:
#   - Ver tabelas: \dt
#   - Ver licenças: SELECT * FROM licenses LIMIT 5;
#   - Sair: \q
```

### 🏗️ Rebuild (reconstruir após mudanças no código)

```bash
# Reconstruir a imagem da API (após mudar código Python)
docker compose build api

# Reconstruir E subir
docker compose up -d --build api
```

---

## ⛔ O que NÃO Fazer

| Comando Perigoso | O que faz | Use isso ao invés |
|-----------------|-----------|-------------------|
| `docker system prune -af --volumes` | **APAGA TUDO** incluindo banco de dados! | `docker system prune -f` (sem `--volumes`) |
| `docker compose down -v` | Remove containers **E volumes** (dados perdidos!) | `docker compose down` (sem `-v`) |
| Editar `.env` na VPS sem backup | Se errar, a API não sobe | `cp .env .env.backup` antes de editar |
| `docker compose up` (sem `-d`) | Trava seu terminal | Sempre use `docker compose up -d` |

> ⚠️ **Regra de ouro**: Nunca use `-v` ou `--volumes` em comandos `down` ou `prune` em produção. Isso apaga o banco de dados!

---

## 📁 Onde ficam os dados?

```
/opt/bluebot/
├── .env                    ← Senhas e configurações (NUNCA compartilhe!)
├── docker-compose.yml      ← Define os containers
├── data/
│   ├── ssl/                ← Certificados HTTPS
│   └── backups/postgres/   ← Backups do banco
├── nginx/                  ← Configuração do proxy
├── api/                    ← Código da API (Python)
├── admin/                  ← Painel admin (HTML)
└── client_app/             ← Painel do cliente (HTML)
```

**Dados do banco** ficam em um **volume Docker** chamado `postgres_data`. Mesmo que você remova o container, os dados continuam salvos (a menos que use `down -v`).
