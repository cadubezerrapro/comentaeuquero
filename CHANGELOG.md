# Changelog

## 1.17.0 (2026-11-06)

- **Link mágico:** com `LINK_MAGICO_SEGREDO` (o mesmo na Vercel do ia_thefuture), link
  do funil pra um material (`#item-<id>`) sai assinado pra pessoa que pediu:
  `?ceq=<token>&mg=<validade>.<HMAC>`. O site libera só aquele material, sem login, até
  a validade (`LINK_MAGICO_DIAS`, padrão 30). Funciona nos modos `parametro` e
  `redirecionar`. Sem o segredo, nada muda.
- Busca de Leads acha a pessoa pelo código do link (`ceq`): é como se descobre quem
  repassou um link.

## 1.16.0 (2026-11-06)

- **Lead é só quem entrou num funil.** Direct comum, leitura de mensagem e clique em
  botão de mensagem antiga não criam lead nem consultam o perfil na Meta (menos
  chamadas de API). Lead nasce quando um fluxo ligado começa e ganha
  `entrou_funil_em`. Leads, CSV, contadores do topo e "Leads capturados" do painel
  contam só esses.
- Migração: quem já passou por um fluxo (ou foi importado de planilha) vira lead com a
  data da primeira sessão. Contato antigo de direct comum some das listas, mas não é
  apagado.
- Coluna **Palavra** preenchida também para quem pediu pelo direct, com a palavra que
  a pessoa usou de fato (antes ficava vazia no direct e era sempre a primeira da lista
  no comentário).
- Novo evento **"Pediram, mas o fluxo está desligado"** nos logs: comentário ou direct
  com a palavra de um fluxo desligado aparecia como "sem palavra-chave".
- Lista de fluxos diz "desligado", como o editor (antes dizia "pausado").

## 1.15.1 (2026-11-05)

Acabamento da interface, revisado tela a tela nos temas claro e escuro.

- **Gatilhos:** interruptor corrigido (a bolinha saía do trilho por herdar o estilo de
  botão). Cada gatilho em blocos: título, palavras e as respostas públicas num quadro
  "em rodízio", sem o emoji quebrar sozinho na linha de baixo. Gatilho de texto curto
  não fica mais desalinhado. "Adicionar resposta pública" virou botão secundário.
- **Painéis de passo:** caixas de seleção no tema do app (a nativa saía cinza e
  esticada). Opções rápidas e Ação com rótulo em cada campo ("Texto que a pessoa vê",
  "Apelido da saída", "Marcação"). "Apagar este passo" com cara de ação destrutiva.
- **Agendar:** seletor de data e hora no seu fuso, em vez de digitar ISO em UTC; avisa
  quando a data já passou.
- **Editor:** fluxo comprido abre a 75% no começo do fluxo, em vez de encolher até os
  passos ficarem ilegíveis.
- **Painel:** rádios e caixas no mesmo acabamento do editor; "Baixar histórico" numa
  linha só no computador e em coluna no celular.

## 1.15.0 (2026-11-05)

- **Link rastreado**: o funil do fluxo ganha a etapa *clicaram*. Por padrão o link
  segue com o domínio real e ganha `?ceq=<token>` (só nos domínios de
  `CEQ_LINK_DOMINIOS`); o site de destino avisa a abertura em `POST /r/<token>/visto`.
  Modo opcional `CEQ_LINK_RASTREADO=redirecionar` passa por `/r/<token>` (302, mesmo
  destino pra robô e pessoa, sem cloaking). Botão de link também é rastreado.
- **Quem deixou de seguir**: tarefa de fundo, uma vez por dia, reconfere os seguidores
  com a etiqueta `isca_viral`. Quem parou ganha a etiqueta `deixou_de_seguir` e a data
  aparece em Leads e no CSV. Só lê, devagar, para no primeiro sinal de limite da Meta
  e nunca marca "segue" quando a Meta não informa. `POST /api/seguidores/reconsultar`
  roda na hora.
- **Segue a conta: pedido, não muro.** A Condição pede o follow e, depois de pedir
  (*Pedir pra seguir até*, padrão 1 por sessão), entrega mesmo sem o follow. A Meta não
  aceita travar conteúdo atrás do follow, e o muro prendia em loop quem a API não
  mostra como seguidor. `libera_apos: 0` mantém o muro, por escolha explícita.
- Corrigido: perfil devolvido sem o campo de seguidor era gravado como "não segue"
  (0); agora fica desconhecido (vazio), como a Condição já previa.
- **Teto de mensagens com link** (`CEQ_LINKS_HORA`, padrão 60/h): num pico de
  comentários, a mensagem com URL espera a vez em vez de sair em rajada e fazer o
  Instagram pausar os links da conta.
- Editor de fluxos ganha o botão de tema claro/escuro no pé da lateral, o mesmo do
  painel (a escolha vale nos dois).

## 1.14.0 (2026-11-04)

- Modais e dropdowns no estilo do painel, no painel e no editor de fluxos. Saem a
  janela cinza do navegador (confirmar, perguntar nome, avisar) e o menu nativo
  dos campos de seleção. Os modais têm fundo desfocado, foco preso, Esc e Enter;
  ações destrutivas aparecem em vermelho. Os dropdowns abrem pra cima quando falta
  espaço, aceitam teclado (setas, Enter, Esc, digitar a inicial) e respeitam tema
  claro e escuro. Um arquivo só: `app/static/ceq-ui.js`.

## 1.13.1 (2026-11-04)

- Resposta a comentário com texto seguido de botões (ou respostas rápidas) sai numa
  mensagem só: o texto vira o corpo dos botões. A Meta aceita uma única private reply
  até a pessoa responder, e os botões mandados depois voltavam com code 10 / subcode
  2534022 ("fora da janela permitida"). Por DM direta nada muda.

## 1.13.0 (2026-11-04)

- **Logs do sistema** (menu, abaixo de Leads): diário completo da instância, com
  filtros (só erros, envios, fluxos, webhooks, conta e acesso), busca por @, fluxo
  ou código de erro, contador de erros nas últimas 24h, detalhe de cada evento e
  atualização automática opcional.
- Falha de envio agora guarda o motivo da Meta (http, code, subcode e mensagem).
  Antes o evento de texto, mídia e carrossel só dizia "Falha no envio".

## 1.12.0 (2026-11-03)

Primeira versão deste repositório (cadubezerrapro/comentaeuquero), mantida por
Cadu Bezerra (Licença de Uso Sustentável 1.0).

- Removida a ativação por `CLUB_TOKEN`: a instância não manda mais ping, versão,
  contagem de leads nem id de instalação para nenhum servidor externo. As únicas
  saídas de rede são Meta, Anthropic (se o nó de IA estiver ligado) e Telegram (se
  o alerta estiver configurado).
- Removidos `CLUB_TOKEN`, `ACTIVATION_URL`, `CHAO_URL` e `CHAO_VERSAO`, o aviso de
  assinatura no painel e o campo `licenca` do `/health` e do MCP.
- Removidos o `docker-compose.club.yml` (watchtower apontando para imagem externa),
  o site de divulgação e o script de exportação interno.
- Tutoriais movidos para `docs/`, sem o instalador externo.
- Imagem Docker publicada em `ghcr.io/cadubezerrapro/comentaeuquero`.

### Segurança
- Container roda como usuário comum (uid 10001), não mais como root.
- Cabeçalhos `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e
  `Referrer-Policy: same-origin` em todas as respostas.
- Requisição que muda estado com o cookie do painel e origem de outro site é recusada
  (403), além do `SameSite=Lax` que já existia.
- Nó "chamar webhook": só aceita `http://` e `https://` e o prazo fica entre 1 e 30 s.
- Dependências do editor atualizadas (`npm audit`: 0 vulnerabilidades) e editor
  recompilado a partir do código-fonte.
