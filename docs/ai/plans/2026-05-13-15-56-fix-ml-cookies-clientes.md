# Plano: Corrigir ML_COOKIES remoto e aba Clientes

## Analise da situacao atual

- O painel admin em `admin/index.html` possui a aba `clients`, mas o bloco JavaScript contem um fechamento extra logo apos `loadClients()`, quebrando a continuidade do objeto Alpine.
- O servico `config_service.upsert_config` atualmente so atualiza campos criptografados quando o valor e truthy. Isso impede sobrescrever/limpar credenciais com string vazia e dificulta garantir persistencia fiel do cookie vindo do painel.
- O executavel/bot busca configuracao remota e monitora alteracoes, mas a sincronizacao inicial de credenciais para `os.environ` foi removida. O conversor do Mercado Livre ainda le `ML_COOKIES` diretamente do ambiente.
- O template Docker de cliente nao monta `./.env:/app/.env`, entao qualquer escrita feita dentro do container nao atualiza o `.env` do cliente no host.

## Problemas identificados

1. **Critico: aba Clientes quebrada**
   - Impacto: a navegacao do console falha ao clicar em Clientes.
   - Causa provavel: `},` extra apos `loadClients()`.
   - Esforco: baixo.

2. **Critico: ML_COOKIES remoto nao aplicado ao runtime**
   - Impacto: alteracoes no painel podem chegar ao banco, mas o conversor usa o ambiente antigo.
   - Causa provavel: falta de sincronizacao inicial e incompleta entre config remota e `os.environ`.
   - Esforco: medio.

3. **Alto: `.env` do cliente nao e atualizado no host**
   - Impacto: apos restart do container, variaveis alteradas remotamente podem voltar ao valor antigo do `env_file`.
   - Causa provavel: template removeu o bind mount do `.env`.
   - Esforco: baixo/medio.

4. **Medio: campos secretos nao aceitam limpeza explicita**
   - Impacto: painel nao consegue remover uma credencial ja salva.
   - Causa provavel: update condicional por truthiness.
   - Esforco: baixo.

## Solucao proposta

- Remover o fechamento extra no JavaScript e manter `loadClients()` dentro do objeto Alpine.
- Restaurar atualizacao de campos criptografados por `is not None`, permitindo salvar valores novos e limpar com string vazia.
- Centralizar sincronizacao de credenciais remotas no executavel:
  - atualizar `os.environ` na carga inicial e no watcher;
  - persistir campos selecionados em `.env` quando houver arquivo montado/escrevivel;
  - registrar log sanitizado com tamanho do `ML_COOKIES`, sem expor valor.
- Restaurar o bind mount `./.env:/app/.env` no template de cliente para que a persistencia dentro do container reflita no host.
- Adicionar testes focados para proteger as duas regras de maior risco: update/limpeza de `ml_cookies` e sintaxe/estrutura minima do JS do painel.

## Pros e contras

- Pros:
  - Corrige a causa direta da aba Clientes.
  - Garante que o Mercado Livre use cookies novos sem depender de restart manual.
  - Mantem compatibilidade com o fluxo Docker atual e torna a persistencia clara.
  - Evita expor o cookie em logs.
- Contras:
  - Persistir `.env` dentro do container exige o bind mount no cliente.
  - Atualizar `.env` com credenciais remotas aumenta a necessidade de proteger permissao do arquivo no servidor.

## Cronograma de implementacao

1. Criar backup do estado atual.
2. Escrever testes de regressao.
3. Corrigir `config_service.py`, `executable/main.py`, `clientes/template/docker-compose.yml` e `admin/index.html`.
4. Rodar testes automatizados e validacoes de sintaxe.
5. Documentar mudancas e passos de deploy.

## Riscos e mitigacoes

- Risco: conflito com alteracoes locais existentes.
  - Mitigacao: backup via stash antes das edicoes e leitura do diff atual.
- Risco: `.env` montado como read-only ou inexistente no container.
  - Mitigacao: falhar de forma nao fatal e manter sincronizacao em memoria.
- Risco: logs vazarem cookie.
  - Mitigacao: logar apenas comprimento/presenca.

## Criterios de sucesso

- `admin/index.html` passa em validacao basica de sintaxe do script.
- `loadClients()` permanece funcional e a aba Clientes renderiza a lista derivada de licencas ativas.
- `PUT /config/{license_key}` e `PUT /admin/licenses/{id}/config` conseguem atualizar `ml_cookies`.
- O bot sincroniza `ML_COOKIES` na inicializacao e em alteracoes posteriores.
- O template de cliente monta `.env` no bot para permitir persistencia no host.
