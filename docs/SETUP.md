# BlueBot — Como Provisionar um Novo Cliente

## Pré-requisitos

- Infraestrutura (postgres + api + nginx) rodando
- Rede `bluebot_network` criada
- Chave de licença gerada no painel admin

## Método Automático (Recomendado)

```bash
cd /opt/bluebot
bash scripts/novo-cliente.sh <slug>
```

O script vai:
1. Pedir as informações do cliente (licença, Telegram, etc.)
2. Criar `clientes/<slug>/` com docker-compose e .env
3. Subir os containers automaticamente
4. Verificar saúde dos containers

## Método Manual

### 1. Criar diretório
```bash
mkdir -p /opt/bluebot/clientes/<slug>
```

### 2. Copiar template
```bash
cp clientes/template/docker-compose.yml clientes/<slug>/
sed -i "s/\${CLIENTE_SLUG}/<slug>/g" clientes/<slug>/docker-compose.yml
```

### 3. Criar .env
```bash
cat > clientes/<slug>/.env << EOF
CLIENTE_SLUG=<slug>
LICENSE_KEY=APRO-XXXX-XXXX-XXXX
CLIENT_PASSWORD=<senha>
APRO_API_BASE=http://bluebot_api:8000
TELEGRAM_API_ID=<id>
TELEGRAM_API_HASH=<hash>
TELEGRAM_PHONE=<telefone>
TELEGRAM_SOURCES=<canais>
TELEGRAM_DESTINATION=<destino>
WHATSAPP_ENDPOINT=http://whatsapp_<slug>:4000
DOCKER_CONTAINER=1
EOF
chmod 600 clientes/<slug>/.env
```

### 4. Subir containers
```bash
cd clientes/<slug>
docker compose up -d
docker compose logs -f  # Monitorar
```

## Remover Cliente

```bash
bash scripts/remover-cliente.sh <slug>
```

## Verificar Saúde

```bash
bash scripts/health-check.sh
```
