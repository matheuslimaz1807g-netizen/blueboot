# 🔒 BlueBot — Sistema de Licenças (Modo Gerenciado)

> **Versão 2.0+**: Todos os robôs devem funcionar em **Modo Gerenciado** com licença vinculada.

---

## ✅ Como Iniciar o Robô

### 🎯 Fluxo Automático (Recomendado)

**O robô NÃO precisa de LICENSE_KEY no .env!** Fluxo automático:

1. `INSTALL_TOKEN` vem de `/opt/bluebot/shared/bot-secrets.env` (rode `./scripts/sync-bot-secrets.sh`)
2. Execute o robô com `LICENSE_KEY=` vazia
3. Máquina aparece em **Admin → Pendentes**
4. Vincule à licença → bot salva a chave em `data/license_key.txt`
5. Reinícios usam o cache — **sem editar .env**

Configuração do cliente (somente isso no `.env`):
```
LICENSE_KEY=
CLIENT_PASSWORD=...
APRO_API_BASE=http://bluebot_api:8000
```

### ❌ "INSTALL_TOKEN inválido"

**Causa**: Token ausente ou diferente do `.env` da API.

**Solução**:
```bash
cd /opt/bluebot
./scripts/sync-bot-secrets.sh
cd clientes/<slug>
docker compose up -d --force-recreate bot_<slug>
```

Não coloque `INSTALL_TOKEN` nem `LICENSE_KEY` no `.env` do cliente.

2. **Robô se registra no Painel**:
   ```
   ⏳ Nenhuma LICENSE_KEY detectada.
   📋 INFORMAÇÕES DESTA MÁQUINA:
      Machine ID:  a1b2c3d4e5f6...
      Hostname:    bot_apenaspromo
      Platform:    Linux
   
   ✅ Robô aguardando aprovação no Painel Admin...
      📱 Vá ao Painel → Pendentes → Vincular
      ⏱️ Tentando a cada 10 segundos...
   ```

3. **Autorize no Painel Admin**:
   - Acesse o admin
   - Vá em **Pendentes**
   - Clique em **Vincular** e escolha a licença (ex: APRO-3JCL-...)

4. **Robô recebe LICENSE_KEY automaticamente** e salva em `data/license_key.txt`:
   ```
   🎉 LICENÇA AUTORIZADA PELO PAINEL!
      Chave: APRO-3JCL-BYPN***
      Salva em data/license_key.txt — reinício sem editar .env
   ```

---

## ⚙️ Configuração (`.env` do cliente)

```env
LICENSE_KEY=
CLIENT_PASSWORD=sua_senha
APRO_API_BASE=http://bluebot_api:8000
```

**Pronto!** `INSTALL_TOKEN` fica em `/opt/bluebot/shared/bot-secrets.env` (infra), não no cliente.

---

## 📡 Configurações Remotas via Painel

Após autorização, **TUDO** vem do Painel Admin:

- ✅ Canais/Grupos Telegram (SOURCE/DESTINATION)
- ✅ Grupos WhatsApp (WHATSAPP_DESTINATIONS)
- ✅ Chaves de Afiliados (Shopee, AliExpress, Mercado Livre)
- ✅ Status (Ativo/Parado)
- ✅ Delays e comportamentos

**Você NÃO precisa editar `.env` local** para essas coisas.

---

## ❌ Erros Comuns

### ❌ "Robô aguardando aprovação no Painel Admin..."

**Significado**: Tudo OK! O robô está esperando você vincular no painel.

**Solução**:
1. Acesse o Painel Admin → **Pendentes**
2. Localize a máquina pelo **Machine ID** (mostrado no log)
3. Clique em **Vincular** e escolha a licença
4. Robô recebe a licença automaticamente em ~10 segundos

### ❌ "Não conseguiu conectar ao painel"

**Causa**: 
- `APRO_API_BASE` está incorreta
- Painel está offline
- Problemas de rede/firewall

**Solução**:
```bash
curl http://bluebot_api:8000/health
```

### ❌ "INSTALL_TOKEN inválido"

**Causa**: Token ausente ou diferente do `.env` da API.

**Solução**:
```bash
cd /opt/bluebot
chmod +x scripts/sync-bot-secrets.sh
./scripts/sync-bot-secrets.sh
cd clientes/apenaspromo
# Atualize o docker-compose do template se ainda for antigo:
cp ../template/docker-compose.yml ./docker-compose.yml
sed -i "s/\${CLIENTE_SLUG}/apenaspromo/g" docker-compose.yml
docker compose up -d --force-recreate bot_apenaspromo
```

### ❌ "Sinal de licença perdido após 30 minutos"

**Causa**: Robô perdeu contato com servidor de licenças.

**Solução**:
- Verifique conexão de rede
- Verifique se Painel está online
- Reinicie o robô

---

## 🔄 Fluxo Completo de Inicialização

```
STARTUP
  │
  ├─ LICENSE_KEY no env? ─────────────── sim ──► validar
  │                                              │
  ├─ cache data/license_key.txt? ─────── sim ──► validar
  │                                              │
  └─ não ──► POST /license/discover ─────────────┤
               (INSTALL_TOKEN da infra)          │
               │                                 │
               ▼                                 ▼
         Pendentes no painel              machine_id vinculado
               │                                 │
               ▼                                 ▼
         Admin vincula ──► assigned_key ──► salva cache ──► BOT RODANDO
```

---

## 💾 Cache de Licença

Após o vínculo no painel, a chave fica em `data/license_key.txt` (volume Docker).

- ✅ Reinício do container **sem** editar `.env`
- ✅ Cache de validação online permite grace period se a API cair

---

## 📞 Suporte

- **Painel Admin**: painel BlueBot
- **Documentação**: `executable/README_LICENCAS.md`

---

**Última atualização**: Julho 2026  
**Versão**: BlueBot 2.0+

