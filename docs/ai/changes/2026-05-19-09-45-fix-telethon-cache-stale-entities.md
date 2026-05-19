# Mudanças Realizadas: Correção de Stale Cache do Telethon ao Resolver Fontes

**Data/Hora**: 2026-05-19 09:45

## Mudanças Realizadas
1. **Resolução Forçada via ResolveUsernameRequest (`executable/bot_runner.py`)**:
   - Modificado o loop de resolução de fontes de origem.
   - Sempre que a fonte de origem for baseada em username (não numérica), o bot agora executa primeiro a chamada RPC `ResolveUsernameRequest` do Telegram.
   - Isso atualiza de forma forçada o banco de dados do SQLite do Telethon (`.session` local) com as informações e IDs corretos e atualizados, contornando o bug de cache antigo do Telethon.
   - Caso falhe, há um fallback automático para o `client.get_entity` tradicional.

## Testes Realizados
- O script foi compilado sem erros de sintaxe via `python -m py_compile`.
- A integração foi feita de forma resiliente, protegendo contra usernames inválidos com Try/Catch e fallback para o comportamento original.

## Impacto na Aplicação
- Elimina o problema de o bot continuar escutando canais antigos mesmo após o usuário ter atualizado o username/link do canal no painel administrativo.
- Melhora a robustez do motor de polling do robô.
