# 🔒 BlueBot — Sistema de Licenças (Modo Gerenciado)

> **Versão 2.0+**: Todos os robôs devem funcionar em **Modo Gerenciado** com licença vinculada.

---

## ✅ Como Iniciar o Robô

### 🎯 Fluxo Automático (Recomendado)

**O robô NÃO precisa de LICENSE_KEY manual!** Ele se registra automaticamente:

1. **Execute o robô** (sem LICENSE_KEY):
   ```bash
   # Windows
   .\ApenasPromo.exe
   
   # Linux/macOS
   ./main.py
   ```

2. **Robô se registra no Painel**:
   ```
   ⏳ Nenhuma LICENSE_KEY detectada.
   📋 INFORMAÇÕES DESTA MÁQUINA:
      Machine ID:  a1b2c3d4e5f6...
      Hostname:    MINHA-PC
      Platform:    Windows 11
   
   ✅ Robô aguardando aprovação no Painel Admin...
      📱 Vá ao Painel, localize esta máquina e clique em AUTORIZAR
      ⏱️ Tentando a cada 10 segundos...
   ```

3. **Autorize no Painel Admin**:
   - Acesse: `https://seu-painel.com/admin`
   - Vá em "Máquinas"
   - Localize esta máquina pelo **Machine ID**
   - Clique em **"AUTORIZAR"**

4. **Robô recebe LICENSE_KEY automaticamente**:
   ```
   🎉 LICENÇA AUTORIZADA PELO PAINEL!
      Chave: a1b2c3d4e5f6***
      Iniciando sistema...
   ```

---

## ⚙️ Configuração (`.env`)

Você **NÃO precisa preencher LICENSE_KEY manualmente**. Apenas configure:

```env
# ── PAINEL DE ADMINISTRAÇÃO ────────────────────────────────────────
APRO_API_BASE=https://seu-painel.com

# Token de instalação (se o painel exigir)
INSTALL_TOKEN=

# Rótulo (opcional)
ROBOT_LABEL=Bot - Máquina Principal

# ── TELEGRAM (Opcional) ────────────────────────────────────────────
API_ID=1234567
API_HASH=abcdef1234567890abcdef1234567890
```

**Pronto!** É só isso. O resto é gerenciado pelo Painel Admin.

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

**Significado**: Tudo OK! O robô está esperando você autorizar no painel.

**Solução**:
1. Acesse o Painel Admin
2. Procure por "Máquinas" ou "Robôs Registrados"
3. Localize a máquina pelo **Machine ID** (mostrado no log)
4. Clique em **"AUTORIZAR"**
5. Robô receberá a licença automaticamente em ~10 segundos

### ❌ "Não conseguiu conectar ao painel"

**Causa**: 
- `APRO_API_BASE` está incorreta
- Painel está offline
- Problemas de rede/firewall

**Solução**:
```bash
# Teste a conexão
curl https://seu-painel.com/health

# Verifique a URL
set APRO_API_BASE=https://seu-painel.com
```

### ❌ "INSTALL_TOKEN inválido"

**Causa**: Token de instalação está errado ou vencido.

**Solução**:
- Verifique o `INSTALL_TOKEN` no `.env`
- Obtenha um novo token no Painel Admin
- Tente novamente

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
  ↓
[1] LICENSE_KEY definida?
  ├─ ✅ SIM → Pula para [4]
  └─ ❌ NÃO → Vai para [2]

[2] Registrar no Painel
  ├─ Envia: Machine ID, Hostname, Platform
  └─ Aguarda resposta a cada 10s

[3] Painel envia LICENSE_KEY?
  ├─ ✅ SIM → Continua para [4]
  └─ ❌ NÃO → Volta para [2]

[4] Validar Licença
  └─ Se OK → Vai para [5]

[5] Carregar Config Remota
  └─ Se OK → Vai para [6]

[6] Iniciar Heartbeat (ping a cada 15min)

[7] Dashboard Pronto! ✅
```

---

## 💾 Cache de Licença

O robô pode armazenar a licença em cache local para funcionar **offline por 30 minutos** (grace period).

Se o servidor ficar offline:
- ✅ Robô continua funcionando por 30 minutos
- ⏱️ Após 30 minutos: Encerra (requer conexão com painel)

---

## 📞 Suporte

- **Painel Admin**: `https://seu-painel.com`
- **Documentação**: `https://seu-painel.com/docs`
- **Suporte**: Entre em contato com o administrador

---

**Última atualização**: Maio 2026  
**Versão**: BlueBot 2.0+

