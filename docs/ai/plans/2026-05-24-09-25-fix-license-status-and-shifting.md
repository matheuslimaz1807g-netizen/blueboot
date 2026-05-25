# Planejamento: Correção de Alinhamento de Colunas e Status Expirado no Painel Admin

## 1. Análise da Situação Atual
Ao analisar o arquivo `/admin/index.html` e a imagem/tabela fornecida pelo usuário, identificamos dois problemas graves correlacionados no Painel Administrativo:

1. **Desalinhamento/Deslocamento de Colunas (Shift Bug)**:
   A tabela de licenças possui **9 colunas de dados (`<td>`)**, mas apenas **8 cabeçalhos (`<th>`)** definidos na tag `<thead>`. Isso faz com que todas as colunas fiquem deslocadas para a esquerda por uma posição:
   - A coluna com cabeçalho "Chave" exibe o Nome do Cliente (`lic.note`).
   - A coluna "Plano" exibe a chave da licença (`lic.key`).
   - A coluna "Status" exibe o plano da licença (`lic.plan`).
   - A coluna "WhatsApp" exibe se a licença está ativa ou inativa no banco (`lic.active`).
   - A coluna "Máquina" exibe o status de conexão do WhatsApp (`lic.whatsapp_status`).
   - A coluna "Expiração" exibe o ID da máquina vinculada (`lic.machine_id`).
   - A coluna "Heartbeat" exibe a data de expiração (`lic.expires_at`).
   - A coluna "Ações" exibe o tempo relativo do Heartbeat (`lic.last_heartbeat`).
   - A coluna real de botões de Ações fica sem cabeçalho associado.

2. **Status "ATIVA" em Licença Expirada**:
   Atualmente, o status da licença exibido na tabela (sob o cabeçalho incorreto "WhatsApp") renderiza apenas o valor do campo booleano `lic.active` do banco de dados (que indica se a chave está habilitada/desabilitada manualmente). 
   Se a data de expiração da licença (`lic.expires_at`) já passou, o sistema backend bloqueia o robô (retornando `valid=False`), mas o Painel Admin continua exibindo o status visual como "ATIVA" porque o campo manual `lic.active` permanece `true`.

## 2. Soluções Propostas

### A. Correção dos Cabeçalhos da Tabela
Adicionaremos o cabeçalho `<th>Cliente</th>` na primeira posição de `<thead>` e manteremos o `<th>Ações</th>` na última posição, totalizando 9 cabeçalhos que se alinharão perfeitamente com os 9 `<td>` da tabela:
```html
<th>Cliente</th>
<th>Chave</th>
<th>Plano</th>
<th>Status</th>
<th>WhatsApp</th>
<th>Máquina</th>
<th>Expiração</th>
<th>Heartbeat</th>
<th>Ações</th>
```

### B. Exibição Dinâmica do Status de Expiração
Atualizaremos a renderização da coluna de **Status** (que passará a estar sob o cabeçalho "Status" correto após o alinhamento) para verificar dinamicamente se a licença está expirada:
- Se `!lic.active` -> Exibe **INATIVA** (Vermelho).
- Se `lic.active` for verdadeiro, mas `lic.expires_at` for menor que a data atual -> Exibe **EXPIRADA** (Vermelho).
- Caso contrário -> Exibe **ATIVA** (Verde).

Exemplo de implementação em Alpine.js:
```html
<span
  class="badge"
  :class="!lic.active ? 'badge-red' : (lic.expires_at && new Date(lic.expires_at) < new Date() ? 'badge-red' : 'badge-green')"
  x-text="!lic.active ? 'INATIVA' : (lic.expires_at && new Date(lic.expires_at) < new Date() ? 'EXPIRADA' : 'ATIVA')"
></span>
```

## 3. Cronograma de Implementação
- **Passo 1**: Fazer backup seguro dos arquivos que serão editados.
- **Passo 2**: Atualizar o arquivo `/admin/index.html` corrigindo os cabeçalhos (`<thead>`) e a lógica do badge de status (`<td>`).
- **Passo 3**: Validar o alinhamento e o comportamento visual no navegador/código.

## 4. Riscos e Mitigação
- **Risco**: Erro de sintaxe na expressão ternária do Alpine.js quebrar a renderização da tabela.
- **Mitigação**: Testar e validar a expressão inline cuidadosamente de forma limpa e legível.
