# ApenasPromo — Bot de Automação com Licença

Sistema completo de automação Telegram/WhatsApp com interface web local, empacotado como executável, com sistema de licenca online e painel admin.

---

## Estrutura do projeto

```
BlueBot/
├── api/            ← FastAPI (servidor de licença e config na VPS)
├── admin/          ← Painel admin (HTML estático servido pelo Nginx)
├── executable/     ← Código-fonte do executável
│   ├── affiliates/ ← Módulos de afiliados
│   ├── web/        ← Templates e CSS/JS embutidos no .exe
│   ├── main.py
│   ├── license.py
│   ├── pipeline.py
│   ├── bot_runner.py
│   ├── config_loader.py
│   ├── updater.py
│   └── build.sh
├── docker-compose.yml
└── .env.example
```

---

## 1. Subir a API na VPS (Ubuntu 22.04)

### Requisitos
- Ubuntu 22.04 LTS
- Docker + Docker Compose v2
- Domínio apontando para o IP da VPS (para HTTPS)

### Passos

```bash
# 1. Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# 2. Clonar / transferir o projeto para a VPS
scp -r ./BlueBot user@seu-servidor:/opt/apenaspromo

# 3. Configurar variáveis de ambiente
cd /opt/apenaspromo
cp .env.example .env
nano .env
```

**Edite o `.env` com valores reais:**
```env
POSTGRES_USER=bluebot
POSTGRES_PASSWORD=uma_senha_muito_forte
POSTGRES_DB=bluebot

# Gere com: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=cole_aqui_32_bytes_hex

# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=cole_aqui_chave_fernet

ADMIN_USERNAME=admin
ADMIN_PASSWORD=senha_do_painel_admin

API_BASE_URL=https://api.seudominio.com
```

```bash
# 4. Subir os serviços
docker compose up -d --build

# Verificar logs
docker compose logs -f api

# Saúde
curl https://api.seudominio.com/health
```

### HTTPS com Certbot (opcional mas recomendado)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.seudominio.com
```

---

## 2. Criar a primeira licença

### Via painel admin web

1. Abra `https://seudominio.com/admin/` no browser
2. Faça login com `ADMIN_USERNAME` / `ADMIN_PASSWORD` do `.env`
3. Clique em **+ Nova licença**
4. Escolha o plano (basic/pro) e a duração em dias
5. Clique em **Gerar Licença** — a chave `APRO-XXXX-XXXX-XXXX` será exibida
6. **Copie a chave agora** — ela não é exibida novamente

### Via curl (alternativo)
```bash
# 1. Login (obter token)
TOKEN=$(curl -s -X POST https://api.seudominio.com/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"sua_senha"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Criar licença de 30 dias
curl -X POST https://api.seudominio.com/admin/licenses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan":"basic","expires_days":30}'
```

---

## 3. Configurar o cliente (config da licença)

Após criar a licença, defina as configurações no painel admin:

1. Na tabela de licenças, clique em **Config**
2. Preencha:
   - **Telefone**: número do Telegram do cliente
   - **Fontes**: URLs dos grupos a monitorar (uma por linha)
   - **Destino Telegram**: URL ou @username do canal destino
   - **Endpoint WhatsApp**: ex. `http://localhost:4000/send`
   - **Credenciais de afiliados**: tokens/keys do Shopee, AliExpress e ML
3. Clique em **Salvar**

> As credenciais são criptografadas com Fernet antes de serem salvas no banco.

---

## 4. Gerar o executável

### No Windows (PowerShell)

```powershell
cd executable

# Instalar dependências
pip install -r requirements.txt

# Definir a URL da API (bake into exe via env var que o código lê)
$env:APRO_API_BASE = "https://api.seudominio.com"

# Executar o build
bash build.sh
# ou se não tiver bash:
pyinstaller --onefile --name "ApenasPromo" `
  --add-data "web/templates;web/templates" `
  --add-data "web/static;web/static" `
  --hidden-import "telethon" --hidden-import "flask" `
  --hidden-import "httpx" --hidden-import "cryptography" `
  --collect-all "telethon" --collect-all "flask" `
  --noconfirm --clean main.py

# Resultado: dist\ApenasPromo.exe
```

### No Linux (para build Linux)

```bash
cd executable
pip install -r requirements.txt
APRO_API_BASE=https://api.seudominio.com bash build.sh
# Resultado: dist/ApenasPromo
```

> **Importante**: Edite `main.py` e `license.py` para hardcoded `API_BASE` antes de buildar para distribuição, para que clientes não possam alterar.

---

## 5. Obfuscação com Cython (opcional — anti-engenharia reversa)

Protege `license.py` e `pipeline.py` convertendo-os em binários nativos:

```bash
pip install cython

# Criar setup_cython.py
cat > setup_cython.py << 'EOF'
from setuptools import setup
from Cython.Build import cythonize
setup(
    ext_modules=cythonize(
        ["license.py", "pipeline.py"],
        compiler_directives={"language_level": "3"},
    )
)
EOF

# Compilar (requer gcc no Linux ou Visual Studio Build Tools no Windows)
python setup_cython.py build_ext --inplace

# Remover fontes Python (PyInstaller usará os .pyd/.so)
rm license.py pipeline.py

# Agora buildar normalmente com build.sh
```

---

## 6. Distribuir o executável para o cliente

```
dist/
└── ApenasPromo.exe   ← arquivo único para distribuir
```

1. Envie **somente** o `ApenasPromo.exe` para o cliente
2. O cliente executa o `.exe` — o browser abre automaticamente em `http://localhost:8080/activate`
3. O cliente digita a chave `APRO-XXXX-XXXX-XXXX`
4. Na primeira ativação, a máquina é vinculada à licença (bind irreversível)
5. Após ativar, o cliente acessa o painel, inicia o bot, pronto

**Nenhum arquivo de código é exposto ao cliente.**  
**Todas as credenciais ficam no servidor e são baixadas em memória.**

---

## 7. Publicar uma atualização

```bash
# 1. Gerar novo executável com versão atualizada
# Edite VERSION = "1.1.0" em main.py
bash build.sh

# 2. Gerar SHA-256
sha256sum dist/ApenasPromo.exe
sha256sum dist/ApenasPromo

# 3. Hospedar os binários (ex: GitHub Releases, S3, servidor web próprio)
# URL pública dos arquivos: https://seudominio.com/downloads/ApenasPromo-1.1.0.exe

# 4. Cadastrar a versão via painel admin:
#    Aba "Versões" → + Publicar versão → preencher version, URLs e SHA-256
```

Na próxima execução do executável pelo cliente, o auto-updater:
1. Detecta que há versão mais nova no `/version/latest`
2. Baixa o novo binário
3. Verifica o SHA-256
4. Substitui o executável atual
5. Reinicia automaticamente

---

## Variáveis de ambiente — referência completa

| Variável | Descrição |
|----------|-----------|
| `POSTGRES_USER` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL |
| `POSTGRES_DB` | Nome do banco |
| `JWT_SECRET` | Segredo para assinar tokens JWT do admin |
| `FERNET_KEY` | Chave Fernet para criptografar credenciais |
| `ADMIN_USERNAME` | Login do painel admin |
| `ADMIN_PASSWORD` | Senha do painel admin |
| `API_BASE_URL` | URL pública da API (usada pelo Nginx e pelo executável) |
| `RATE_LIMIT_PER_MINUTE` | Limite de requisições por IP/minuto |
| `APP_VERSION` | Versão da API |

---

## Segurança

- Flask local escuta **apenas** em `127.0.0.1:8080` — inacessível pela rede
- Credenciais de afiliados nunca são escritas em disco no cliente
- `config.json` local contém apenas `license_key` e `machine_id`
- Machine binding: na primeira ativação, o SHA-256 do MAC+hostname é vinculado à chave
- Licenças com `machine_id` diferente são rejeitadas imediatamente
- Heartbeat a cada 30 minutos; grace period offline de 4 horas
- Fernet AES-128-CBC + HMAC para credenciais no banco

---

## Comandos úteis (VPS)

```bash
# Ver logs da API em tempo real
docker compose logs -f api

# Reiniciar a API
docker compose restart api

# Acessar o banco PostgreSQL
docker compose exec postgres psql -U bluebot -d bluebot

# Rebuild após mudanças no código
docker compose up -d --build api

# Parar tudo
docker compose down
```
