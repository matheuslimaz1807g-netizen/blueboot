# Plano: correcao de envio para canais do WhatsApp

## Analise da situacao atual

O servico `Whatsapp/server.js` recebe posts em `/send`, enfileira a mensagem e usa `client.sendMessage` do `whatsapp-web.js` para grupos e canais. O destino `channel:Apenas PROMO - Ofertas 24h` esta sendo encontrado corretamente, mas o envio para canal com midia falha dentro do codigo injetado da biblioteca com `msg.avParams is not a function`.

A versao instalada da biblioteca e `whatsapp-web.js` 1.34.7, vinda diretamente do GitHub (`pedroslopez/whatsapp-web.js`). O trecho interno de canais chama `msg.avParams()` para montar `mediaMetadata`. No WhatsApp Web atual, o modelo de mensagem criado nesse fluxo pode nao expor esse metodo.

Tambem ha um problema de observabilidade: `sendToDestinationsInternal` captura o erro por destino, apenas registra log e nao sinaliza falha para a fila. Por isso aparece `[Queue] Envio concluido.` mesmo quando nenhum destino recebeu a mensagem.

## Problemas identificados

1. Critico: envio de midia para canal quebra em `msg.avParams is not a function`.
   - Impacto: posts com imagem/caption nao chegam ao canal.
   - Esforco: medio.

2. Alto: fila marca envio como concluido mesmo com falha em todos os destinos.
   - Impacto: falso positivo operacional e dificulta diagnostico.
   - Esforco: baixo.

3. Medio: dependencia do GitHub sem patch local explicito.
   - Impacto: rebuild pode manter ou trocar comportamento sem clareza.
   - Esforco: medio.

## Solucoes propostas

### Opcao A: patch runtime no servidor

Aplicar, apos `ready`, um patch defensivo no contexto do WhatsApp Web para adicionar `avParams` ao prototype do modelo de mensagem quando o metodo nao existir.

Pros:
- Mantem a correcao em arquivo da aplicacao.
- Sobrevive ao rebuild Docker.
- Evita editar `node_modules` diretamente.
- Baixo risco para grupos e mensagens de texto.

Contras:
- Depende de APIs internas do WhatsApp Web, assim como a propria biblioteca.
- Deve ser mantido enquanto a biblioteca nao estabilizar esse caminho.

### Opcao B: editar diretamente `node_modules/whatsapp-web.js`

Trocar `msg.avParams()` por fallback local.

Pros:
- Corrige exatamente a linha que falha.

Contras:
- Nao e confiavel em rebuilds.
- Mistura codigo de terceiros com codigo da aplicacao.
- Dificulta rastrear manutencao.

### Opcao C: atualizar/trocar versao da biblioteca

Buscar uma versao com suporte atualizado a canais.

Pros:
- Pode remover a necessidade de patch.

Contras:
- Exige rede, validacao maior e pode quebrar autenticacao/envios existentes.
- Como a dependencia ja vem do GitHub, a variabilidade aumenta.

## Decisao tecnica

Usar a Opcao A, com patch runtime localizado e logs claros, e corrigir a semantica de sucesso da fila. E a abordagem mais conservadora para resolver o erro atual com menor impacto no restante do sistema.

## Cronograma de implementacao

1. Criar backup via `git stash push`.
2. Adicionar patch runtime no `server.ts` e no `server.js`, pois o container executa `server.js`.
3. Ajustar retorno de `sendToDestinationsInternal` para contabilizar sucessos e falhas.
4. Garantir que a fila lance erro quando todos os destinos falharem.
5. Adicionar documentacao da mudanca em `docs/ai/changes`.
6. Validar sintaxe Node e comportamento estrutural.

## Riscos e mitigacoes

- Risco: `mediaMetadata` exigir campos diferentes em alguma versao do WhatsApp Web.
  - Mitigacao: `avParams` retorna `toJSON()` quando disponivel e inclui campos de midia conhecidos do modelo.

- Risco: patch falhar silenciosamente se os modulos internos mudarem de nome.
  - Mitigacao: registrar log de sucesso/falha do patch.

- Risco: alterar comportamento de sucesso da fila afetar logs existentes.
  - Mitigacao: manter sucesso por destino e usar erro agregado apenas quando nenhum destino for enviado.

## Criterios de sucesso

- O erro `msg.avParams is not a function` nao deve mais ocorrer no envio de midia para canal.
- A fila nao deve registrar `Envio concluido` quando todos os destinos falharem.
- Grupos continuam usando `client.sendMessage` normalmente.
- `server.js` deve passar em verificacao de sintaxe Node.
