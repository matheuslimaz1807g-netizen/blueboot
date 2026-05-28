# Plano de Produto e Engenharia: Curadoria Humanizada (Anti-Bot)

Como engenheiro focado em produto e conversão, concordo 100% com você. O maior erro das operações de afiliados hoje é a **"Fadiga de Ofertas"** — o usuário percebe o padrão robótico (sempre o mesmo texto, mesmos emojis, horários matemáticos) e desenvolve *banner blindness* (cegueira a anúncios). O canal vira um catálogo chato e a taxa de clique (CTR) despenca.

Para o BlueBot se destacar no mercado e atrair comunidades reais, precisamos evoluir de um **"Repassador de Links"** para um **"Curador Especialista"**.

Abaixo estão as 4 estratégias de Produto/Tech que proponho implementarmos.

## 1. Motor de Copywriting Dinâmico e Reescrita (IA ou Templates)

O maior sintoma de um bot é a padronização do texto. Quando copiamos e colamos o texto original da oferta, ele soa como um encarte de supermercado.

**Proposta Selecionada: Abordagem Offline (Spintax Dinâmico)**
Como temos uma audiência inicial de 12 seguidores, não há necessidade de custos com APIs (OpenAI/Gemini). Vamos construir um **Motor de Spintax Local**, criando um banco de "Gatilhos de Abertura", "Meios" e "Fechamentos" variados. O código irá sortear e concatenar essas frases para dar um tom 100% humano (ex: "Galera, achei essa pérola..." + "Preço absurdo!" + link).

## 2. Injeção de "Opinião" Baseada no Score Matemático

Nós já temos o brilhante `offer.score` no `offer_filter.py`. Vamos usá-lo para marketing. Um humano não tem a mesma empolgação para uma capa de celular de R$10 e um iPhone com 40% de desconto.

**Proposta e Limites de Preço:**
*   **Score > 80 (Nível "Bug"):** O bot usa emojis de sirene 🚨, e frases curtas ("GENTE DO CÉU CORRE!").
*   **Score entre 60 e 79 (Nível "Ótima Oportunidade"):** Tom de recomendação forte ("Para quem tava esperando baixar...").
*   **Score < 60 (Nível "Aviso/Rotina"):** Tom informativo e casual.
*   **Regra de Rejeição por Preço (Filtro Inteligente):** Ofertas com valor muito alto (ex: > R$ 1.500) serão sumariamente **bloqueadas** pelo filtro, exceto se a oferta contiver palavras-chave de alto valor agregado como "iPhone", "TV", "Smart TV", "Notebook". Máquinas de lavar e eletrodomésticos caros genéricos não convertem e serão ignorados.

## 3. Humanização do *Timing* (Jitter e Agrupamento)

Bots respondem em milissegundos. Nós já possuímos o campo `delay_segundos` no painel do cliente, mas atualmente ele funciona como uma espera fixa matemática.

**Proposta:**
*   **Evoluir para Jitter Aleatório:** Fazer com que o `delay_segundos` defina o "tempo máximo" de atraso, e o código aguarde um tempo randômico entre `2` e `delay_segundos`. Isso simula com perfeição o tempo humano de entrar no app e colar o link.
*   **Batching Silencioso:** (Para o futuro) Agrupar ofertas fracas em resumos diários.

## 4. Quebra de Padrão (Conteúdo não-venda)

Grupos que só enviam link de venda morrem. Precisamos de engajamento fantasma.

**Proposta:**
*   Fazer o bot enviar enquetes interativas automáticas 1x ao dia (ex: *"O que vocês estão procurando comprar nessa semana?"*).
*   Fazer o bot reagir (dar *like* ou *fire* 🔥) nas próprias postagens ou nas postagens de administradores.
*   Fazer com que 1 a cada 20 mensagens não tenha link, apenas engajamento: *"Vocês viram que a Amazon tá com frete grátis na madruga hoje? Fiquem de olho que vou mandar os melhores aqui."*
