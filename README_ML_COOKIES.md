# 🔧 RESUMO DAS CORREÇÕES - Botão Compartilhar ML

## ✅ Já Implementado

### 1. Detecção melhorada de página de login
- Agora detecta quando título é apenas "Mercado Libre" (seu caso exato!)
- Verifica presença de elementos de usuário logado
- Mensagens de erro mais específicas

**Arquivo**: `executable/affiliates/mercadolivre.py` (linhas 103-119 e 48-86)

### 2. Injeção de cookies mais robusta
- Cookies injetados com atributos completos
- Melhor tratamento de erros
- Log detalhado de cada cookie injetado

---

## 🚨 O Problema Real

Na VPS, os cookies salvos em `ML_COOKIES` estão:
- **Expirados** (TTL excedido)
- **Inválidos para o IP da VPS** (proteção anti-fraude do ML)

No Windows funciona porque usa seu **perfil logado do Brave** (não depende de cookies injetados).

---

## 🎯 PRÓXIMOS PASSOS (Para você resolver)

### ⚡ Solução Rápida (5 minutos):

1. **Windows - Extrair cookies novos**:
   ```
   Brave → Mercado Livre → LOGIN
   → Instale extensão "Cookie Editor"
   → Export cookies para `.mercadolivre.com.br`
   → Copie resultado (formato: cookie1=val1;cookie2=val2;...)
   ```

2. **VPS - Atualizar .env**:
   ```bash
   ssh seu-vps
   nano /opt/apenaspromo/.env
   # Adicione/atualize:
   ML_COOKIES=cookie1=val1;cookie2=val2;cookie3=val3
   ```

3. **VPS - Reiniciar**:
   ```bash
   docker compose restart
   ```

4. **Teste**:
   ```bash
   docker compose logs -f | grep "Compartilhar"
   # Deve ver: ✓ Clicou em 'Compartilhar'
   # E NÃO: ✗ Detectada página de LOGIN
   ```

---

## 📖 Documentação Completa

Veja: `SOLUCAO_ML_COOKIES.md` (instruções detalhadas com screenshots e alternativas)

---

## ✨ Resultado Esperado

**Antes** (com cookies expirados):
```
[DEBUG] Título da página atual: Mercado Libre
[WARNING] Detectada página de LOGIN. A sessão (ML_COOKIES) pode ter expirado...
[ERROR] Falha ao clicar em 'Compartilhar'
```

**Depois** (com cookies válidos):
```
[DEBUG] Título da página atual: Kit Com 10 Cuecas Boxer Microfibra Adulto Usee Brasil
[DEBUG] Clicou em 'Compartilhar'
[DEBUG] Clicou em 'Copiar link'
[DEBUG] Link Final: https://meli.la/xxxxx
```

---

## 💡 Dica Extra

Se quiser testar **antes** de atualizar a VPS:

```python
# No Windows, crie test_ml.py:
import os
os.environ['ML_COOKIES'] = 'seu_cookie_aqui=valor1;outro_cookie=valor2'

from executable.affiliates.mercadolivre import _gerar_link_mercadolivre_sync
link = _gerar_link_mercadolivre_sync('https://meli.la/2f5H1zk')
print(link)
```

---

**Dúvidas?** Consulte `SOLUCAO_ML_COOKIES.md` para alternativas e debug avançado.
