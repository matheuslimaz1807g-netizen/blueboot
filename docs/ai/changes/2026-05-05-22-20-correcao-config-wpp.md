# Mudança: Correção na Sobreposição de Configurações de WhatsApp

## Mudanças Realizadas
- **Refatoração do `config_loader.py`**:
  - Adicionada função `merge_configs` para realizar a mesclagem inteligente entre configurações locais (.env) e remotas (API de Licença).
  - Adicionada proteção contra valores `None` ou vazios no `whatsapp_endpoint`.
- **Atualização do `main.py`**:
  - Alterada a lógica de inicialização para carregar primeiro o `.env` e usar a API remota apenas para sobrepor campos preenchidos.
  - Isso garante que, se o Painel Admin não tiver grupos configurados, o bot use os grupos definidos localmente no `.env`.
- **Ajuste no `bot_runner_vps.py`**:
  - Adicionada a mesma proteção contra endpoints nulos encontrada no `main.py`.

## Razão para cada mudança
- O bot estava perdendo as configurações de WhatsApp porque a API remota retornava valores nulos ou vazios, que "atropelavam" as configurações locais corretas.

## Testes adicionados/modificados
- Criado script de teste unitário `test_config_merge.py` para validar a lógica de mesclagem (Local vs Remoto).

## Impacto na aplicação
- O bot agora é muito mais resiliente a configurações incompletas no Painel Admin.
- O WhatsApp voltará a funcionar usando o `.env` como fallback automático se a API remota falhar ou estiver vazia.

## Próximos passos recomendados
- Verificar no Painel Admin se as configurações de WhatsApp estão preenchidas para evitar a necessidade do fallback local no futuro.
