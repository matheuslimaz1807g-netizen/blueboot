# Correção SSL ERR_CERT_COMMON_NAME_INVALID — 2026-05-12

## Problema
O navegador bloqueava `app.bluebotapp.com.br` com erro `net::ERR_CERT_COMMON_NAME_INVALID`.

## Causa Raiz Identificada

A IA anterior (conversas de 08-09/Mai/2026) fez uma série de commits que quebraram o SSL:

| Commit | O que fez | Impacto |
|--------|----------|---------|
| `a48e5cc` | Criou `nginx/nginx.conf` e mudou volume mount para `./nginx/nginx.conf` | Começou a usar config separada |
| `2eeef94` | Mudou **todos** os paths SSL de `/etc/letsencrypt/live/...` para `/etc/nginx/ssl/` | **QUEBROU SSL** |
| `2eeef94` | Mudou volume de `./ssl/letsencrypt:/etc/letsencrypt` para `./ssl:/etc/nginx/ssl` | Certificados inacessíveis |
| `2d95bb7` | Substituiu todo docker-compose.yml por apenas serviços de cliente | Removeu nginx da raiz |

### Diagrama do problema:

```
ANTES (funcionando):
  docker-compose.yml → nginx → /etc/letsencrypt/live/bluebotapp.com.br/
  Volume: ./ssl/letsencrypt:/etc/letsencrypt

DEPOIS (quebrado pela IA anterior):
  docker-compose.yml → nginx → /etc/nginx/ssl/ (PATH ERRADO!)
  Volume: ./ssl:/etc/nginx/ssl (VOLUME ERRADO!)
```

## Mudanças Realizadas

### 1. `nginx/nginx.conf` — Corrigido paths SSL
- **De:** `/etc/nginx/ssl/fullchain.pem` (10 ocorrências)
- **Para:** `/etc/letsencrypt/live/bluebotapp.com.br/fullchain.pem`
- **Adicionado:** Configuração CORS no bloco da API (que estava faltando)
- **Mantido:** Blocos `/panel/` e `/app_static/` adicionados pela IA anterior

### 2. `nginx.conf` (raiz) — Sincronizado
- Tornado **idêntico** ao `nginx/nginx.conf` para evitar confusão futura
- Agora ambos os arquivos são intercambiáveis

### 3. `core/docker-compose.yml` — Adicionado volume client_app
- Adicionado mount `../client_app:/usr/share/nginx/html/client:ro`
- Necessário para servir `/app_static/` definido no nginx.conf

### 4. `fix-ssl.sh` — Criado script de diagnóstico
- Detecta automaticamente todos os problemas SSL
- Verifica paths montados, certificados, SANs, e conectividade
- Fornece instruções de correção específicas

## Próximos Passos na VPS

### Opção A: Se usando `core/docker-compose.yml`
```bash
cd /opt/bluebot
git pull
cd core
docker compose restart nginx
```

### Opção B: Se usando `docker-compose.yml` da raiz (versão antiga)
```bash
cd /opt/bluebot  # ou /usr/blueboot
git pull
# O docker-compose.yml da raiz não tem mais nginx!
# Precisa usar core/docker-compose.yml:
cd core
docker compose up -d
```

### Opção C: Se nginx usa config customizada na VPS
```bash
# Executar diagnóstico
chmod +x fix-ssl.sh && ./fix-ssl.sh

# Copiar config corrigida para o local usado
cp nginx.conf /caminho/montado/pelo/docker/
# OU
cp nginx/nginx.conf /caminho/montado/pelo/docker/

# Reiniciar
docker restart bluebot_nginx
```

## Impacto
- **Risco:** Baixo — apenas corrige caminhos de arquivo
- **Requer deploy:** Sim — precisa reiniciar nginx na VPS
- **Dados afetados:** Nenhum — apenas configuração
