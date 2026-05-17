# Mudancas: refatoracao clean UI dos paineis

## Mudancas realizadas

- Refatorado `client_app/index.html` para uma linguagem visual mais operacional:
  - removidos glassmorphism, fundo radial, gradiente principal, sombras exageradas e cantos muito arredondados;
  - adicionados contratos visuais `.panel-surface`, `.panel-muted`, `.brand-mark` e `.clean-ui-contract`;
  - cards, inputs, header e login ficaram mais densos e consistentes.
- Refatorado `admin/index.html` na camada de estilos e componentes centrais:
  - cards, modais, toasts, inputs, tabelas, botoes e navegacao receberam raio menor, sombra discreta e espacamento mais contido;
  - titulos principais foram reduzidos para uma hierarquia mais profissional;
  - removido uso residual de `accent-gradient`.
- Atualizados testes estaticos:
  - `api/tests/test_admin_panel_static.py`;
  - `api/tests/test_client_app_static.py`.
- Registrado backup em `docs/ai/backups.md`.

## Razao das mudancas

- Reduzir sinais visuais comuns de layout gerado por IA, como gradientes chamativos, glass cards, sombras pesadas, cantos grandes e composicao promocional.
- Manter a paleta atual do BlueBot, preservando a identidade visual ja existente.
- Fazer a melhoria sem alterar endpoints, Alpine state, autenticacao, modelos de dados ou regras de negocio.

## Testes adicionados/modificados

- Adicionados testes de contrato clean UI para garantir ausencia de `glass`, `accent-gradient`, `rounded-3xl`, `rounded-2xl` e `shadow-2xl` nos paineis relevantes.
- Mantidos os testes existentes de sintaxe JavaScript e contratos funcionais.

## Validacao executada

- `node` validou a sintaxe dos scripts inline de `admin/index.html` e `client_app/index.html`.
- `node` executou assercoes equivalentes aos novos contratos visuais estaticos.
- `pytest` nao foi executado porque:
  - `pytest` nao esta disponivel no PATH;
  - `python` nao esta disponivel no PATH;
  - `py` aponta para Python da Microsoft Store com acesso negado;
  - o Python empacotado do Codex existe, mas nao possui o modulo `pytest` instalado.

## Impacto na aplicacao

- Impacto funcional esperado: nenhum.
- Impacto visual: paineis com aparencia mais limpa, menos gerada por template e mais adequada a ferramenta SaaS operacional.

## Proximos passos recomendados

- Rodar a suite `pytest` completa em um ambiente com Python/pytest instalados.
- Fazer uma revisao visual em navegador autenticado ou com dados mockados para calibrar densidade de tabelas, estados vazios e modais.
