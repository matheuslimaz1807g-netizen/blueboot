# Plano: Correção de Stale Cache do Telethon ao Resolver Fontes

## Situação Atual
O usuário alterou o canal de origem (Grupos de origem) no painel administrativo para `https://t.me/testemfoox`. O robô (BotRunner) lê a configuração do painel com sucesso e tenta resolver a fonte `https://t.me/testemfoox`. No entanto, ele resolve a fonte para um ID e título antigo (`TESTE` com ID `3809484442`), que não corresponde ao canal correto atual.

## Problemas Identificados
1. **Cache Persistente de Entidades do Telethon**: A biblioteca Telethon salva de forma persistente todas as entidades (usuários, grupos e canais) no arquivo `.session` (banco de dados SQLite).
2. **get_entity() do Cache**: Quando chamamos `client.get_entity('username')`, se o username existir na tabela de cache local do arquivo `.session`, o Telethon retorna o ID antigo armazenado em cache sem fazer uma requisição real à API do Telegram. Se o usuário recriou o grupo/canal ou alterou o username, o bot fica preso monitorando o ID antigo.

## Soluções Propostas
- **Usar ResolveUsernameRequest**: Antes de chamar `get_entity` padrão para um username, podemos fazer a chamada direta do método RPC `ResolveUsernameRequest` do Telegram. Isso força uma consulta fresca ao servidor do Telegram, ignorando o cache local e atualizando automaticamente o banco de dados do Telethon com o novo ID e metadados.

### Prós:
- Atualização em tempo real das fontes sem necessidade de deletar manualmente arquivos de sessão.
- Extremamente robusto e à prova de alteração de usernames/handles de canais.
- Mantém a compatibilidade total com IDs numéricos (que continuam usando `get_entity` diretamente).

### Contras:
- Um pequeno request de rede extra por fonte baseada em username durante o startup (apenas quando o bot inicia/reinicia).

## Cronograma de Implementação
1. Criar este plano de ação.
2. Fazer backup local utilizando `git stash`.
3. Atualizar a resolução de fontes em `executable/bot_runner.py` utilizando `ResolveUsernameRequest` da biblioteca Telethon.
4. Validar o código.
5. Comitar e fazer push das mudanças.
6. Documentar as alterações.

## Riscos Potenciais e Mitigação
- **FloodWaitError**: Fazer muitas resoluções de username em sequência pode acionar limites do Telegram.
  - *Mitigação*: A resolução é feita uma única vez no início do bot ou quando as configurações mudam, o que é muito infrequente. Além disso, envolve apenas fontes não numéricas.

## Critérios de Sucesso
- O bot de origem deve conseguir resolver e monitorar o ID correto e atualizado do canal de origem inserido no painel sem puxar informações antigas em cache.
