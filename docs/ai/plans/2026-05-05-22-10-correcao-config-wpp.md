# Plano: Correção da Sobreposição de Configuração de WhatsApp

## Análise da Situação Atual
O bot está relatando `Destinos=[]` e `Endpoint=None` no log de inicialização, apesar de o usuário indicar que as configurações deveriam estar presentes. Isso ocorre porque o bot, ao rodar no modo "Gerenciado" (com licença), baixa a configuração remota da API. Se essa configuração contiver valores nulos (`null`) ou listas vazias para os campos de WhatsApp, eles sobrepõem as variáveis de ambiente locais do `.env`.

## Problemas Identificados
1. **Precedência Destrutiva**: A configuração remota substitui integralmente a local, em vez de complementar.
2. **Valores Nulos na API**: A API de licenciamento parece estar retornando `whatsapp_endpoint: null`, o que causa o erro `Endpoint=None` no log (já que o `.get()` do Python retorna o valor se a chave existe, mesmo que seja `None`).
3. **Parsing de Listas**: Se a variável de ambiente não é carregada corretamente, o parser de lista resulta em `[]`.

## Soluções Propostas
1. **Merge Inteligente de Configuração**: No arquivo `main.py`, implementar uma lógica de mesclagem onde a configuração local serve como base (default) e apenas valores não nulos e não vazios da API remota fazem a sobreposição.
2. **Reforço de Defaults em `config_loader.py`**: Garantir que as funções de carregamento nunca retornem `None` para campos obrigatórios, mesmo que o `.env` ou a API os forneçam como nulos.
3. **Melhoria de Logging**: Informar no log se um campo está vindo do `.env` ou da Configuração Remota.

## Cronograma de Implementação
- [ ] **Sessão 1**: Backup e TDD (Simular config com valores nulos).
- [ ] **Sessão 2**: Modificar `executable/config_loader.py` para sanitizar retornos.
- [ ] **Sessão 3**: Modificar `executable/main.py` para realizar o merge.
- [ ] **Sessão 4**: Verificação final e documentação.

## Riscos Potenciais e Mitigação
- **Risco**: Configuração remota intencionalmente vazia (ex: desativar todos os grupos) ser ignorada pela lógica de merge.
- **Mitigação**: Priorizar a flag `ENABLE_WHATSAPP` remota, mas manter os destinos locais se a lista remota for nula.

## Critérios de Sucesso
- O log inicial deve mostrar os destinos configurados no `.env` se a API remota estiver vazia.
- `Endpoint` não deve mais aparecer como `None`.
