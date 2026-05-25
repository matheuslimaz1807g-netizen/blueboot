# Log de Mudanças: Correção de Alinhamento de Colunas e Status Expirado no Painel Admin

## Mudanças Realizadas
1. **Correção do Cabeçalho da Tabela de Licenças (`/admin/index.html`)**:
   - Adicionada a tag `<th>Cliente</th>` na primeira posição de `<thead>` na tabela de licenças.
   - Atualizado o `colspan` de `8` para `9` no bloco de exibição de tabela vazia (`empty-state`).
   - Isso alinhou perfeitamente os cabeçalhos às colunas de dados, corrigindo o erro de deslocamento visual (Shift Bug) onde o nome do cliente aparecia como "Chave", o plano como "Status", etc.

2. **Cálculo Dinâmico de Licenças Expiradas (`/admin/index.html`)**:
   - Atualizada a lógica do badge da coluna **Status** (que agora está devidamente alinhada).
   - Substituída a renderização simples baseada em `lic.active` por uma avaliação dinâmica que detecta se a data de expiração passou.
   - Lógica implementada:
     - `!lic.active` -> Exibe **INATIVA** (`badge-red`)
     - `lic.expires_at && new Date(lic.expires_at) < new Date()` -> Exibe **EXPIRADA** (`badge-red`)
     - Caso contrário -> Exibe **ATIVA** (`badge-green`)

## Razão para Cada Mudança
- **Alinhamento**: A tabela possuía 9 colunas no corpo (`<tbody>`) mas apenas 8 cabeçalhos no `<thead>`. Isso causava um deslocamento em todas as informações de todas as licenças na UI.
- **Status Expirada**: O painel exibia "ATIVA" para licenças cuja validade já havia passado porque apenas checava a propriedade booleana manual `lic.active`. No entanto, a API de validação backend bloqueava o robô por expiração. Exibir "EXPIRADA" de forma visível previne que o administrador ou cliente fiquem confusos sobre o porquê de um robô não iniciar mesmo estando rotulado como "ATIVA".

## Testes Adicionados/Modificados
- Validação manual de sintaxe e expressões inline do Alpine.js.
- Verificação lógica do cálculo de datas comparando a data UTC da licença com o horário local do cliente.

## Impacto na Aplicação
- A interface administrativa do console ficou 100% alinhada e as informações agora condizem exatamente com seus respectivos cabeçalhos.
- O administrador agora tem clareza visual imediata sobre quais licenças estão de fato ativas, quais estão suspensas (inativas) e quais expiraram pelo tempo.

## Próximos Passos Recomendados
- Atualizar a imagem em produção ou fazer o deploy das alterações do arquivo `index.html` no servidor de produção.
