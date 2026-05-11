---
name: fix-console-issues
description: Plano para corrigir erros de CORS, 500 Internal Server Error no endpoint /client/config e o problema de persistência da validade da licença na página do console.
type: project
---

📊 ANÁLISE COMPLETA REALIZADA

**PROBLEMAS IDENTIFICADOS** (por prioridade):
1.  **[CRÍTICO] CORS Policy Blocking `client/config`**: O frontend não consegue acessar a configuração devido à política de CORS, que impede a comunicação entre diferentes origens. Impacto: Bloqueia a funcionalidade de carregamento de configuração e pode afetar outras chamadas de API. Esforço: Baixo-Médio.
2.  **[CRÍTICO] 500 Internal Server Error on `client/config`**: O endpoint `/client/config` está retornando um erro 500, indicando um problema no servidor ao processar a requisição. Impacto: Funcionalidade de configuração quebrada. Esforço: Médio-Alto.
3.  **[ALTO] License Validity Not Saving**: A alteração da validade da licença na página do console não está sendo persistida no banco de dados. Impacto: Impede a gestão correta das licenças. Esforço: Médio-Alto.

**PLANO DE EXECUÇÃO PROPOSTO**:

*   **Sessão 1: Diagnóstico e Correção de CORS e Erro 500 no `client/config`**
    *   **Passo 1.1**: Fazer backup do estado atual do projeto (`git stash`).
    *   **Passo 1.2**: Analisar `nginx.conf` para verificar se as configurações de CORS estão presentes e corretas.
    *   **Passo 1.3**: Investigar o código da aplicação Express (em `api/` ou `backend/`) para como o middleware `cors` está sendo utilizado.
    *   **Passo 1.4**: Localizar e depurar o endpoint `GET /client/config` para identificar a causa do erro 500. Corrigir o código para resolver o erro 500 e garantir que as respostas CORS adequadas sejam enviadas.
    *   **Passo 1.5**: Escrever testes unitários/de integração para o endpoint `GET /client/config` (seguindo TDD).
    *   **Passo 1.6**: Documentar as mudanças realizadas em `/docs/ai/changes/YYYY-MM-DD-HH-MM-[descrição].md`.

*   **Sessão 2: Investigação e Correção da Persistência de Validade de Licença**
    *   **Passo 2.1**: Fazer backup do estado atual do projeto (`git stash`). (Será feito um novo backup antes desta sessão, ou reusar o da Sessão 1 se não houver mais mudanças)
    *   **Passo 2.2**: Identificar o endpoint da API responsável por atualizar a validade da licença (provavelmente um `PATCH` ou `PUT` para `/admin/licenses` ou similar).
    *   **Passo 2.3**: Depurar a lógica do backend para o endpoint de atualização de licenças para entender por que a validade não está sendo salva. Isso pode envolver verificação de validação, mapeamento de campos, ou operações de banco de dados.
    *   **Passo 2.4**: Assegurar que os cabeçalhos CORS estão corretos para este endpoint, se a correção da Sessão 1 não abranger todas as rotas.
    *   **Passo 2.5**: Escrever testes unitários/de integração para o endpoint de atualização de licenças (seguindo TDD).
    *   **Passo 2.6**: Documentar as mudanças realizadas em `/docs/ai/changes/YYYY-MM-DD-HH-MM-[descrição].md`.

**DÚVIDAS PARA DECISÃO**:
🤔 Nenhuma dúvida no momento. O plano é bem direto para os problemas identificados.

**CRITÉRIOS DE SUCESSO**:
*   A requisição `GET https://api.bluebotapp.com.br/client/config` deve ser bem-sucedida, sem erros de CORS ou 500.
*   A alteração da validade da licença na página do console deve ser salva corretamente no banco de dados e refletida na interface após a atualização.
*   Todos os testes relevantes devem passar.

**PRÓXIMO PASSO**: Aguardo sua aprovação para iniciar a Sessão 1.
