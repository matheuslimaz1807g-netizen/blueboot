# Mudanca: Limpeza de seguranca e publicacao no Git

## Mudancas realizadas

- Removidos do versionamento artefatos sensiveis/inuteis:
  - `test_api.py`
  - `.env.bak`
  - `token.txt` e `token_clean.txt`
  - `ssl/cert.pem` e `ssl/key.pem`
  - `backend/prisma/dev.db` e journal
  - `executable/config.json`
  - `executable/.wwebjs_auth/`
  - `Drivers/`, `Screenshots/`, `bot bkp.py`, `temp_115154.jpg`
  - `.claude/settings.local.json`
- Reescrito `.gitignore` para bloquear ambientes, segredos, certificados, sessoes, bancos locais, caches, drivers e outputs.
- Substituidos segredos reais em `.env.example` por placeholders.
- `docker-compose.yml` agora exige `POSTGRES_PASSWORD` e `DATABASE_URL` via ambiente.
- `api/app/core/config.py` nao contem mais defaults secretos; valida placeholders inseguros e deriva `JWT_SECRET` de variaveis privadas quando ausente.
- `api/app/core/security.py` nao faz mais fallback para chave Fernet hardcoded.
- `executable/main.py` passa a exigir `DASHBOARD_PASSWORD`.

## Razao para cada mudanca

- Sessoes, cookies, chaves privadas, tokens e bancos locais nao devem existir no repositorio.
- `test_api.py` estava obsoleto, duplicava testes e continha credenciais/endpoints antigos.
- Defaults secretos no codigo reduzem a seguranca quando uma implantacao sobe sem `.env` correto.

## Testes adicionados/modificados

- Mantidos os testes novos em `api/tests/test_public_license_routes.py`.
- Nenhum teste novo foi necessario para remocao de artefatos.

## Validacao executada

- `python -m pytest api\tests -q`
- `python -m compileall api\app executable`
- Scan local por strings sensiveis conhecidas.

## Impacto na aplicacao

- Deploys agora precisam fornecer variaveis obrigatorias no `.env`.
- O painel local do executavel exige `DASHBOARD_PASSWORD`.
- Sessoes WhatsApp locais precisarao ser recriadas fora do Git quando necessario.

## Proximos passos recomendados

- Rotacionar credenciais que ja apareceram no historico do repositorio.
- Se necessario, fazer limpeza de historico Git com ferramenta dedicada em uma janela separada.
