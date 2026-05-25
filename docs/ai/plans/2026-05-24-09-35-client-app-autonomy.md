# Planejamento: Autonomia de Configuração no Painel do Cliente (SaaS)

## 1. Análise da Situação Atual
Atualmente, o painel do cliente (`client_app/index.html`) permite que o cliente final configure apenas 4 opções básicas:
- Canal/Grupo de Destino do Telegram
- Fontes Monitoradas
- Se deve enviar para o Telegram (checkbox)
- Se deve enviar para o WhatsApp (checkbox)

O usuário solicitou que o painel dê autonomia total ao cliente, permitindo configurar todas as credenciais e parâmetros (ID/Token da Shopee, AliExpress, Mercado Livre, API ID/Hash do Telegram, Cookies, telefone, delay em minutos, destinos adicionais de WhatsApp), **exceto** o campo de `whatsapp_endpoint` (que deve ser controlado apenas pelo administrador do sistema).

## 2. Soluções Propostas

### A. Proteção no Backend (`api/app/routers/client.py`)
Para garantir máxima segurança contra adulteração de requisições HTTP maliciosas por parte do cliente final, faremos o seguinte no endpoint `PUT /client/config`:
1. Carregar as configurações existentes do banco de dados para a respectiva licença.
2. Sobrescrever o campo `whatsapp_endpoint` do payload enviado pelo cliente final com o valor já persistido no banco de dados.
3. Chamar o serviço de atualização de forma segura. Isso garante que o cliente final não conseguirá alterar a rota do Node.js de WhatsApp, preservando a integridade da infraestrutura Docker/VPS.

### B. Interface do Cliente Completa (`client_app/index.html`)
Adicionaremos campos organizados para todas as configurações requisitadas, utilizando a mesma estética dark premium com TailwindCSS e Alpine.js:
- **Seção Telegram & Geral**:
  - API ID
  - API Hash
  - Telefone
  - Destino Telegram
  - Fontes Monitoradas (Separadas por vírgula)
  - Minutos na fila (com conversão em tempo real de segundos para minutos: `config.delay_segundos / 60`)
- **Seção Afiliados**:
  - Shopee Token
  - AliExpress App Key
  - AliExpress Secret
  - AliExpress Tracking ID
  - Mercado Livre Token
  - ML Cookies (textarea)
- **Seção WhatsApp**:
  - Destinos WhatsApp (separados por vírgula)
- **Seção de Disparo & Integração (Checkboxes)**:
  - Enviar Telegram
  - Enviar WhatsApp
  - Conversor Shopee
  - Conversor AliExpress
  - Conversor Mercado Livre

### C. Ajuste na Carga e Salvamento de Dados (`client_app/index.html`)
Ajustaremos os métodos `loadConfig()` e `saveConfig()` do AlpineJS para inicializar e serializar o campo `wpp_destinations_str` de/para o array `wpp_destinations`.

## 3. Cronograma de Implementação
- **Passo 1**: Realizar backup das alterações atuais no Git.
- **Passo 2**: Implementar a proteção de `whatsapp_endpoint` no backend em `/api/app/routers/client.py`.
- **Passo 3**: Atualizar o painel do cliente `/client_app/index.html` com o formulário expandido e a lógica do Alpine.js.
- **Passo 4**: Testar as modificações e atualizar logs de backups e log de mudanças.
