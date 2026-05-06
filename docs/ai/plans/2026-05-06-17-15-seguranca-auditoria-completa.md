# PLANEJAMENTO DETALHADO - AUDITORIA DE SEGURANÇA BLUEBOT

## Data: 2026-05-06 17:15
## Tipo: Auditoria de Segurança Completa

---

## 1. ANÁLISE DA SITUAÇÃO ATUAL

### Contexto
Projeto BlueBot é um sistema de automação (Telegram/WhatsApp) com:
- API FastAPI para gerenciamento de licenças e configurações
- Backend em Python com PostgreSQL
- Frontend em Nginx
- Contêineres Docker
- Sistema de licenciamento SaaS

### Ambiente Atual
- Diretório: `/c/Users/mathe/Downloads/BlueBot`
- Branch: `v2-development`
- Status Git: 1 arquivo modificado (admin.py - debug logging removido)

---

## 2. PROBLEMAS IDENTIFICADOS

### [CRÍTICO] - 7 Vulnerabilidades Críticas

1. **CORS Totalmente Aberto** 
   - Impacto: Qualquer site pode acessar API via navegador (CSRF/XSS)
   - Esforço: BAIXO - 15 min
   - Local: `api/app/main.py:40-44`

2. **Credenciais Expostas no .env**
   - Impacto: Todas as senhas, tokens e chaves visíveis
   - Esforço: MÉDIO - 1 hora
   - Local: `.env` (completo)

3. **Fernet Key Padrão/Insegura**
   - Impacto: Criptografia inútil, dados expostos
   - Esforço: BAIXO - 30 min
   - Local: `api/app/core/security.py:14-30`

4. **JWT Secret Fraca**
   - Impacto: Tokens facilmente quebráveis
   - Esforço: BAIXO - 15 min
   - Local: `api/app/core/config.py:9`

5. **Senha do Banco Fraca**
   - Impacto: Acesso direto ao banco de dados
   - Esforço: BAIXO - 30 min
   - Local: `docker-compose.yml:8`

6. **Senha Admin em Texto Claro no Banco**
   - Impacto: Vazamento direto de credenciais
   - Esforço: MÉDIO - 2 horas
   - Local: `api/app/models/models.py:63`

7. **ML_COOKIES e SESSION_STRING Expostos**
   - Impacto: Sessão WhatsApp/Telegram comprometida
   - Esforço: MÉDIO - 1 hora
   - Local: `.env` linhas 24, 29

### [ALTO] - 7 Vulnerabilidades de Alta Gravidade

1. **Rate Limit Insuficiente**
   - Impacto: Brute force possível
   - Esforço: BAIXO - 30 min
   - Local: `api/app/routers/admin.py:48`

2. **Sem HTTPS (HTTP Plano)**
   - Impacto: Interceptação de dados
   - Esforço: MÉDIO - 2 horas
   - Local: `nginx.conf`

3. **Sem Headers de Segurança**
   - Impacto: XSS, clickjacking, MIME sniffing
   - Esforço: BAIXO - 30 min
   - Local: `nginx.conf`

4. **Bot Monta Perfil Brave do Host**
   - Impacto: Acesso a dados do sistema host
   - Esforço: MÉDIO - 1 hora
   - Local: `docker-compose.yml:98`

5. **Nenhuma Proteção Brute Force Global**
   - Impacto: Ataques de força bruta
   - Esforço: MÉDIO - 2 horas
   - Local: API geral

6. **Imagens Docker Sem Tags Fixas**
   - Impacto: Vulnerabilidades conhecidas não controladas
   - Esforço: BAIXO - 30 min
   - Local: `docker-compose.yml`

7. **Sem Proteção Replay Attack JWT**
   - Impacto: Reutilização de tokens
   - Esforço: ALTO - 3 horas
   - Local: `api/app/core/security.py`

### [MÉDIO] - Outros Problemas

1. Sem proteção contra ataques de dicionário
2. Logs podem conter dados sensíveis
3. Backup de configurações sensíveis
4. Validação de input insuficiente em alguns endpoints

---

## 3. SOLUÇÕES PROPOSTAS

### Solução 1: Restringir CORS (PRIORIDADE 1)
- **Prós**: Bloqueia acessos não autorizados imediatamente
- **Contras**: Pode quebrar integrações legítimas
- **Implementação**: 
  ```python
  allow_origins=["https://painel.bluebot.com", "https://admin.bluebot.com"]
  allow_credentials=True
  ```

### Solução 2: Gerar Secrets Fortes (PRIORIDADE 1)
- **Prós**: Segurança imediata
- **Contras**: Requer redistribuição de configurações
- **Implementação**:
  ```bash
  # Fernet Key
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  
  # JWT Secret  
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

### Solução 3: Hashear Senhas no Banco (PRIORIDADE 1)
- **Prós**: Proteção mesmo com vazamento do banco
- **Contras**: Quebra compatibilidade com senhas existentes
- **Implementação**: Usar `hash_password()` existente

### Solução 4: Configurar HTTPS (PRIORIDADE 2)
- **Prós**: Criptografia em trânsito
- **Contras**: Requer certificados
- **Implementação**: Let's Encrypt + Nginx

### Solução 5: Headers de Segurança (PRIORIDADE 2)
- **Prós**: Proteção contra XSS, clickjacking
- **Contras**: Nenhum significativo
- **Implementação**: Adicionar headers no Nginx

### Solução 6: Rate Limiting Global (PRIORIDADE 2)
- **Prós**: Previne brute force
- **Contras**: Pode afetar usuários legítimos
- **Implementação**: SlowAPI com Redis

### Solução 7: JWT Refresh Token Rotation (PRIORIDADE 3)
- **Prós**: Previne replay attacks
- **Contras**: Complexidade adicional
- **Implementação**: JWT com jti + refresh tokens

---

## 4. CRONOGRAMA DE IMPLEMENTAÇÃO

### Sessão 1 (17:15-18:00) - Correções Críticas I
- ✅ Restringir CORS
- ✅ Gerar e aplicar secrets fortes
- ✅ Hashear senhas no banco
- ✅ Atualizar .env.example

### Sessão 2 (18:00-19:00) - Correções Críticas II
- ✅ Configurar HTTPS básico
- ✅ Adicionar headers de segurança
- ✅ Rate limit global
- ✅ Remover volume do Brave

### Sessão 3 (19:00-20:00) - Correções Médias
- ✅ Docker tags fixas
- ✅ JWT nonce/jti
- ✅ Proteção replay attack
- ✅ Validar inputs

### Sessão 4 (20:00-20:30) - Validação
- ✅ Testar todas as correções
- ✅ Verificar quebra de funcionalidade
- ✅ Documentar mudanças

---

## 5. RISCOS POTENCIAIS E MITIGAÇÃO

### Risco 1: Quebra de Funcionalidade
- **Mitigação**: Testar cada mudança isoladamente
- **Mitigação**: Manter backups via git stash

### Risco 2: Lockout Administrativo
- **Mitigação**: Testar credenciais antes
- **Mitigação**: Manter fallback

### Risco 3: Incompatibilidade de JWT
- **Mitigação**: Manter tokens existentes válidos
- **Mitigação**: Fazer rollout gradual

### Risco 4: Tempo de Downtime
- **Mitigação**: Fazer mudanças em janela de manutenção
- **Mitigação**: Rollback rápido via git

---

## 6. CRITÉRIOS DE SUCESSO

- [ ] Score de segurança > 8/10
- [ ] Nenhuma vulnerabilidade CRÍTICA restante
- [ ] HTTPS funcionando corretamente
- [ ] CORS restrito a domínios autorizados
- [ ] Todas as senhas hasheadas
- [ ] Headers de segurança presentes
- [ ] Testes automatizados passando
- [ ] Zero quebra de funcionalidade existente

---

## 7. DOCUMENTAÇÃO NECESSÁRIA

- [ ] Atualizar README.md com novas configurações
- [ ] Documentar processo de geração de secrets
- [ ] Atualizar .env.example
- [ ] Criar guia de deploy seguro
- [ ] Documentar reversão de mudanças

---