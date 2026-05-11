# Plano: Limpeza de seguranca e publicacao no Git

## Analise da situacao atual

- A branch local e `main`, rastreando `origin/main`.
- Existem alteracoes pendentes da correcao das rotas publicas de licenca.
- O scan local identificou artefatos sensiveis ou inuteis rastreados:
  - `test_api.py` com credencial de teste obsoleta e contratos antigos.
  - `ssl/key.pem` e `ssl/cert.pem`.
  - `.env.bak`, `token.txt`, `token_clean.txt`.
  - sessao real/cache do WhatsApp em `executable/.wwebjs_auth/`.
  - banco local `backend/prisma/dev.db` e journal.
  - defaults sensiveis em `.env.example`, `docker-compose.yml`, `api/app/core/config.py` e fallback Fernet em `api/app/core/security.py`.

## Problemas identificados

1. **Critico: segredos e sessoes rastreadas**
   - Impacto: risco de vazamento de credenciais, sessoes, cookies e chave privada.
   - Esforco: medio.

2. **Alto: defaults de producao no codigo**
   - Impacto: deployments sem `.env` podem subir com credenciais conhecidas.
   - Esforco: medio.

3. **Medio: `test_api.py` obsoleto**
   - Impacto: duplica testes, usa credenciais antigas e endpoints parcialmente divergentes.
   - Esforco: baixo.

4. **Medio: `.gitignore` corrompido/incompleto**
   - Impacto: novos artefatos sensiveis podem voltar ao repositorio.
   - Esforco: baixo.

## Solucao proposta

- Remover do versionamento os artefatos sensiveis/inuteis claramente identificados.
- Atualizar `.gitignore` para impedir reincidencia.
- Trocar exemplos por placeholders seguros.
- Fazer a aplicacao falhar na inicializacao quando segredos obrigatorios estiverem ausentes/inseguros.
- Manter testes automatizados focados e remover apenas `test_api.py` como duplicado obsoleto.

## Riscos e mitigacao

- **Deploy sem variaveis obrigatorias pode falhar**: mitigado porque `.env.example` documenta placeholders e producao deve usar `.env` real.
- **Remover sessoes WhatsApp rastreadas pode exigir novo login local**: aceitavel, pois sessoes nao devem viver no Git.
- **Segredos continuam no historico Git anterior**: documentar necessidade de rotacionar credenciais e limpar historico em uma tarefa dedicada se necessario.

## Criterios de sucesso

- `test_api.py` removido.
- Arquivos sensiveis removidos do index.
- `.gitignore` cobre `.env*`, SSL local, tokens, bancos locais e sessoes.
- Testes Python passam.
- Commit criado e push realizado para `origin/main`.
