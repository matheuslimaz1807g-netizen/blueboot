# Solução: Botão "Compartilhar" - Mercado Livre não autenticado na VPS

## 🔍 Problema Identificado

O bot não consegue gerar links de afiliados do Mercado Livre na **VPS** porque:

1. **Título da página**: Exibe "Mercado Libre" (genérico) ao invés do título do produto
2. **Causa raiz**: Os cookies (`ML_COOKIES`) estão expirados ou inválidos para o IP da VPS
3. **Por que funciona no Windows**: Usa o perfil logado do Brave browser localmente

### Logs de Diagnóstico

```
[DEBUG] Título da página atual: Mercado Libre
↓
[WARNING] Detectada página de LOGIN. A sessão (ML_COOKIES) pode ter expirado ou ser inválida para este IP.
```

---

## ✅ Correções Implementadas

### 1. Enhanced Login Wall Detection

- Detecta agora quando título é **apenas** "Mercado Libre"
- Verifica presença de elementos de usuário logado
- Screenshots de erro melhoradas

### 2. Improved Cookie Injection

- Injeção de cookies mais robusta com atributos completos
- Melhor logging de erros
- Suporte a expiração de cookies configurável

**Arquivo alterado**: `executable/affiliates/mercadolivre.py`

---

## 🔧 Solução Permanente: Regenerar ML_COOKIES

### Opção 1: Extrair cookies do Windows (Recomendado)

#### Passo 1: Instalar extensão de exportação de cookies

1. Abra o **Brave Browser**
2. Vá para `brave://extensions`
3. Busque por **"Cookie Editor"** ou **"Export All Cookies"**
4. Instale uma das extensões

#### Passo 2: Fazer login no Mercado Livre

```
1. Vá para https://www.mercadolivre.com.br
2. Faça login com sua conta
3. Aguarde até estar totalmente logado (veja seu perfil)
```

#### Passo 3: Exportar cookies

1. Clique na extensão de cookies
2. Filtre por domain: `.mercadolivre.com.br`
3. Exporte em formato JSON ou texto
4. Procure especialmente por:
   - `meli_session`
   - `meli_uuid`
   - Cookies com `sid` ou `session` no nome

#### Passo 4: Formatar como variável de ambiente

Se exportado em JSON:

```python
# Converta para string separada por ponto-e-vírgula
# Exemplo:
# cookie1=value1; cookie2=value2; cookie3=value3
```

Se formato de texto, copie tal como está e separe com `;`

#### Passo 5: Atualizar na VPS

1. Acesse o arquivo `.env` da VPS:

   ```bash
   nano /opt/apenaspromo/.env
   ```

2. Procure ou crie a variável:

   ```env
   ML_COOKIES=cookie1=value1;cookie2=value2;cookie3=value3
   ```

3. Salve (`Ctrl+O`, `Enter`, `Ctrl+X`)

4. Reinicie os containers:
   ```bash
   cd /opt/apenaspromo
   docker compose restart
   ```

---

### Opção 2: Usar Script de Extração (Advanced)

Se preferir automatizar, crie `executable/extract_ml_cookies.py`:

```python
#!/usr/bin/env python3
"""
Script para extrair cookies do Mercado Livre usando Selenium
Execute no Windows ou Linux com conta logada
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import sys
import os

def extract_cookies():
    options = Options()
    options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    options.add_argument(f"--user-data-dir=C:\\Users\\{os.getlogin()}\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data")

    driver = webdriver.Chrome(options=options)

    # Acessa ML para carregar cookies
    driver.get("https://www.mercadolivre.com.br")
    input("Faça login se necessário. Pressione Enter quando estiver logado...")

    # Extrai cookies
    cookies = driver.get_cookies()

    # Formata como string
    cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    print("\n📋 Cole isto no .env da VPS:")
    print(f"ML_COOKIES={cookie_string}")

    # Salva em arquivo
    with open("ml_cookies.txt", "w") as f:
        f.write(cookie_string)
    print("\n✅ Cookies salvos em ml_cookies.txt")

    driver.quit()

if __name__ == "__main__":
    extract_cookies()
```

Execute:

```bash
python3 extract_ml_cookies.py
```

---

## 🚨 Problema de IP (Session Binding)

**Mercado Livre pode rejeitar cookies de IPs diferentes** como proteção anti-fraude.

### Solução alternativa: Usar arquivo de preferências do Chromium

Você pode criar um perfil do Chromium na VPS e fazer login lá uma vez:

```bash
# Na VPS
cd /app  # ou onde o app roda
chromium-browser --user-data-dir=/app/chromium-profile https://www.mercadolivre.com.br
# Faça login manualmente
# Fecha navegador
```

Depois, modifique `mercadolivre.py` para usar esse perfil:

```python
if os.name != 'nt':
    # Linux/VPS
    options.add_argument("--user-data-dir=/app/chromium-profile")
```

---

## 🔄 Verificação Pós-Implementação

### Teste 1: Verificar detecção de login

Você deve ver no log:

```
[DEBUG] Título da página atual: Kit Com 10 Cuecas Boxer Microfibra...
```

**Não mais**: "Mercado Libre"

### Teste 2: Verificar injeção de cookies

Logs devem mostrar:

```
[DEBUG] Cookie injetado: meli_session=***
[DEBUG] Cookie injetado: meli_uuid=***
```

### Teste 3: Teste de link

Execute:

```bash
docker compose logs -f api | grep -i "compartilhar\|share"
```

---

## 📞 Se ainda não funcionar

### Checklist:

- [ ] Cookies foram extraídos de conta logada no Windows?
- [ ] ML_COOKIES contém pelo menos 3-4 cookies diferentes?
- [ ] Variável está no `.env` sem espaços em volta?
- [ ] Docker foi reiniciado após mudança?
- [ ] Cookies têm menos de 30 dias (não expiraram)?
- [ ] A conta usada não foi bloqueada por atividade suspeita?

### Debug avançado:

```bash
# Ver logs completos do servidor
docker compose logs api | tail -100

# Verificar variável de ambiente dentro do container
docker compose exec api env | grep ML_COOKIES

# Entrar no container interativamente
docker compose exec api bash
python3 -c "import os; print('ML_COOKIES:', os.getenv('ML_COOKIES', 'NOT SET'))"
```

---

## 📚 Referências

- [Selenium WebDriver Cookies](https://www.selenium.dev/documentation/webdriver/interactions/cookies/)
- [Mercado Livre Developer](https://developers.mercadolivre.com.br/)
- [Brave Browser Cookie Management](https://support.brave.com/)

---

## 🎯 Próximas Melhorias (Futuro)

1. **Implementar OAuth2 do Mercado Livre**: Usar API oficial ao invés de Selenium
2. **Cache de Affiliate Links**: Reutilizar links já gerados para não precisar Selenium
3. **Refresh automático de cookies**: Detectar expiração e solicitar renovação
4. **Pool de contas**: Rotacionar múltiplas contas se uma falhar
