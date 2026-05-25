# Log de Mudanças: Autonomia de Configurações no Painel do Cliente

## Mudanças Realizadas

1. **Proteção no Backend (`api/app/routers/client.py`)**:
   - Atualizado o endpoint `PUT /client/config` do painel do cliente (`update_my_config`).
   - Inserida uma verificação de segurança que carrega a configuração atual da licença do banco de dados antes da atualização e força o valor do campo `whatsapp_endpoint` a permanecer idêntico ao já persistido.
   - Isso impede de forma absoluta que o cliente altere ou corrompa o endpoint do WhatsApp, mesmo injetando requisições HTTP arbitrárias.

2. **Expansão de Campos no Painel do Cliente (`client_app/index.html`)**:
   - Redesenhada a seção "Configurações" para fornecer uma visualização organizada por categorias com rolagem vertical (`max-h-[600px] overflow-y-auto`).
   - Adicionados os seguintes novos campos ao formulário do cliente final:
     - **Geral & Telegram API**: API ID, API Hash, Telefone da Conta, Minutos na Fila (com conversão em tempo real de e para segundos) e Destino Telegram.
     - **WhatsApp**: Grupos/Canais de Destino no WhatsApp (`wpp_destinations_str`).
     - **Credenciais de Afiliado**: Shopee Token, AliExpress Key, AliExpress Secret, AliExpress Tracking ID, Mercado Livre Token, e cookies do Mercado Livre (`ML Cookies` em campo textarea).
     - **Ativação de Recursos**: Checkboxes para Enviar Telegram, Enviar WhatsApp, Conversor Shopee, Conversor AliExpress e Conversor Mercado Livre.

3. **Lógica JS Otimizada no Alpine (`client_app/index.html`)**:
   - Método `loadConfig` atualizado para converter a lista de destinos do WhatsApp (`cfg.wpp_destinations`) em string amigável separada por vírgula (`wpp_destinations_str`).
   - Método `saveConfig` atualizado para extrair e converter `wpp_destinations_str` de volta para o formato de array esperado pelo backend (`wpp_destinations`), além de parsear o campo `delay_segundos` como inteiro.

## Razão para Cada Mudança
- **Autonomia do Cliente**: Permite ao administrador do BlueBot vender planos onde os clientes trazem suas próprias contas do Telegram, chips de WhatsApp e credenciais/tokens de afiliados (Shopee, AliExpress, Mercado Livre), delegando as atualizações para o próprio painel do cliente final sem intervenção do suporte.
- **Proteção do Endpoint do WhatsApp**: O endpoint de WhatsApp controla a integração Docker com o microsserviço Node do cliente. Se um cliente alterasse esse campo incorretamente, o robô pararia de enviar mensagens. Proteger o campo garante estabilidade sistêmica contínua.

## Testes Adicionados/Modificados
- Validação visual do formulário responsivo no desktop e mobile.
- Testes manuais do parser de dados (string $\leftrightarrow$ array para fontes e destinos de WhatsApp) e conversão de tempo (minutos $\leftrightarrow$ segundos).

## Impacto na Aplicação
- Autonomia e valor comercial agregado para a plataforma SaaS.
- Segurança garantida e zero risco de interrupção nas conexões WhatsApp devido a erros do cliente final.
