# 📚 Git Básico — Para Quem Nunca Usou

## O que é Git?

Git é um **sistema de controle de versão**. Pense assim:

- **Sem Git**: Você salva `projeto_v1.zip`, `projeto_v2_final.zip`, `projeto_v2_final_DEFINITIVO.zip`...
- **Com Git**: Cada alteração é registrada com data, autor e descrição. Você pode voltar a qualquer ponto no tempo.

O **GitHub** é onde o código fica salvo na nuvem (como Google Drive para código).

---

## Fluxo Básico

```
Seu computador (local)              GitHub (remoto)
     │                                    │
     │  git pull ←─────────────────────── │  (baixar atualizações)
     │                                    │
     │  → Você edita arquivos             │
     │                                    │
     │  git add .  (preparar mudanças)    │
     │  git commit (salvar localmente)    │
     │  git push ──────────────────────→  │  (enviar para GitHub)
     │                                    │
```

---

## Comandos Essenciais

### Ver o estado atual

```bash
# "Quais arquivos mudaram?"
git status

# Resultado:
# modified:   nginx/conf.d/api.conf     ← arquivo modificado
# new file:   scripts/novo-script.sh    ← arquivo novo
# deleted:    arquivo-velho.txt         ← arquivo removido
```

### Salvar mudanças (commit)

```bash
# 1. Preparar TODOS os arquivos modificados
git add .

# 2. Salvar com uma mensagem descritiva
git commit -m "fix: corrigir CORS no nginx"

# Dica: A mensagem deve explicar O QUE você fez, não COMO
# ❌ Ruim:  "mudanças"
# ❌ Ruim:  "editei o api.conf"
# ✅ Bom:   "fix: corrigir CORS duplicado no nginx"
# ✅ Bom:   "feat: adicionar backup automático do postgres"
```

### Baixar atualizações

```bash
# Baixar mudanças do GitHub para seu computador/VPS
git pull
```

### Enviar mudanças

```bash
# Enviar seus commits para o GitHub
git push
```

---

## Na VPS

```bash
# O fluxo na VPS é simples:
cd /opt/bluebot
git pull                     # Baixar código novo
docker compose build api     # Reconstruir se necessário
docker compose up -d         # Aplicar mudanças
```

---

## O que NUNCA commitar

O arquivo `.gitignore` já protege, mas lembre-se:

| Arquivo | Por quê |
|---------|---------|
| `.env` | Contém senhas! |
| `data/` | Banco de dados e certificados SSL |
| `node_modules/` | Dependências (baixadas automaticamente) |
| `__pycache__/` | Cache do Python |

### Como verificar se o .env está protegido

```bash
# Deve mostrar ".env" na lista
cat .gitignore | grep ".env"
```

---

## Desfazer Mudanças

```bash
# Desfazer mudanças em um arquivo (ANTES do commit)
git checkout -- nginx/conf.d/api.conf

# Desfazer o último commit (mantém os arquivos)
git reset --soft HEAD~1

# Voltar para exatamente o que está no GitHub (CUIDADO: perde mudanças locais!)
git fetch origin
git reset --hard origin/main
```

> ⚠️ `git reset --hard` apaga todas as mudanças locais não commitadas!
