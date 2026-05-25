# Log de Mudanças: Suporte Simultâneo e Separado para Canais e Grupos WhatsApp

Data/Hora: 2026-05-25 19:42
Autor: Antigravity

## Mudanças Realizadas

### 1. Servidor WhatsApp (Node.js)
* **`Whatsapp/server.ts` & `Whatsapp/server.js`**:
  * Implementada a função `refreshTargets()` que unifica a busca de canais (`client.getChannels()`) e grupos (`client.getChats()`), catalogando-os pelo atributo `type` (`"channel" | "group"`).
  * Substituída a rotina de envio por `sendToDestinationsInternal()`, que analisa os alvos configurados.
  * Suporta detecção inteligente de prefixo:
    * Alvos com prefixo `channel:Nome` são encaminhados a canais.
    * Alvos com prefixo `group:Nome` são encaminhados a grupos.
    * Alvos sem prefixo (legados) são buscados genericamente por nome para manter retrocompatibilidade integral.

### 2. Painel Cliente (SaaS)
* **`client_app/index.html`**:
  * Separado o input visual em dois campos:
    * **Canais de Destino no WhatsApp** (vinculado a `config.wpp_channels_str`)
    * **Grupos de Destino no WhatsApp** (vinculado a `config.wpp_groups_str`)
  * Implementadas rotinas em Alpine.js no `loadConfig()` e `saveConfig()` para mapear a array genérica `wpp_destinations` a esses campos adicionando/removendo os prefixos `channel:` e `group:`.

### 3. Painel Administrativo Central
* **`admin/index.html`**:
  * Realizada a mesma divisão de inputs e lógica de desserialização/serialização do `client_app` para assegurar consistência total nos dois painéis web de gerenciamento.

### 4. Painel de Configuração Local
* **`executable/web/templates/config.html`**:
  * Dividida a caixa de texto de destinos em duas áreas de texto (`cfg-wpp-channels` e `cfg-wpp-groups`), realizando a devida junção com quebras de linha (`\n`) e prefixação no salvamento.

### 5. Engine Python e Logs
* **`executable/pipeline.py`**:
  * Tratados os logs de envio e debug para exibir de forma limpa as marcas `Canal(Nome)` ou `Grupo(Nome)` ao remover dinamicamente os prefixos de forma amigável para o cliente.

## Razão para as Mudanças
* Atender à nova diretriz do cliente de manter ambos os canais de comunicação (canais e grupos) funcionando de forma híbrida e independente, controlados por interfaces limpas e organizadas.

## Testes e Validação
* Compilação TypeScript executada com sucesso (`npx tsc`), gerando a versão compilada em `server.js` em sincronia total com `server.ts`.
* Sintaxe Python checada e homologada através do módulo `py_compile`.
