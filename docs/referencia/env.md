# Configuração (.env)

Todas as variáveis que a instância lê. Depois de mudar o `.env`, rode `docker compose up -d` para valer.

## Essenciais

| Variável | Padrão | Para quê |
|---|---|---|
| `BASE_URL` | vazio | Endereço público com `https`, sem barra no fim. Monta o endereço de retorno do login do Instagram e liga o cookie seguro. |
| `WEBHOOK_VERIFY_TOKEN` | `troque-este-token` | Texto que você inventa e cola igual no webhook da Meta. Troque o padrão. |
| `ADMIN_PASSWORD` | vazio | Senha do painel. Se estiver preenchida, vale mais que a senha criada no primeiro acesso. |
| `CEQ_ENCRYPTION_KEY` | vazio | Chave que cifra as credenciais salvas pelo painel. Sem ela, ficam sem cifra e o painel avisa. [Como gerar](../instalar/docker.md). |
| `META_LOGIN_MODO` | vazio | Como conectar o Instagram: `facebook_login` (login unificado, app novo) ou `instagram_login` (app antigo). Vazio = o escolhido no painel; sem escolha, login do Instagram. |
| `META_FB_APP_ID` | vazio | Login unificado: ID do aplicativo (app geral, Configurações do app → Básico). |
| `META_FB_APP_SECRET` | vazio | Login unificado: chave secreta do aplicativo (app geral). Assina os eventos da Meta. |
| `META_FB_CONFIG_ID` | vazio | Login unificado: ID da configuração do login (`config_id`). Não é segredo. |
| `META_APP_ID` | vazio | Login do Instagram (app antigo): ID do app do Instagram. Se preenchido, vale mais que o do painel. |
| `META_APP_SECRET` | vazio | Login do Instagram (app antigo): chave secreta do app do Instagram. Sem a chave do modo em uso (aqui ou no painel), todos os eventos são recusados. |

## IA

| Variável | Padrão | Para quê |
|---|---|---|
| `AI_API_KEY` | vazio | Chave da API da Anthropic, para o passo Resposta com IA. |
| `AI_MODEL` | `claude-haiku-4-5-20251001` | Modelo padrão do passo de IA. |
| `CEQ_IA_POR_LEAD_HORA` | `10` | Quantas respostas de IA a mesma pessoa pode gerar por hora. Passou disso, recebe o texto reserva. |

## Envio

| Variável | Padrão | Para quê |
|---|---|---|
| `CEQ_ENVIOS_HORA` | `180` | Teto inicial de envios por hora. Depois de ajustado em Configurações (de 10 a 750), vale o do painel. |
| `CEQ_LINKS_HORA` | `60` | Teto de mensagens com URL no texto por hora. A Meta segura os links da conta quando muitos saem em pouco tempo (o limite dela não é publicado; este valor é conservador). Passou do teto, a mensagem espera a vez, não se perde. `0` desliga. |

## Rastreamento

| Variável | Padrão | Para quê |
|---|---|---|
| `CEQ_LINK_RASTREADO` | `parametro` | Como medir o clique no link do fluxo. `parametro`: o link segue com o domínio real e ganha `?ceq=<token>`; o site de destino avisa a abertura. `redirecionar`: o link passa por `BASE_URL/r/<token>` (302). `desligado`: nada muda. Ver [Link rastreado](../tutoriais/link-rastreado.md). |
| `CEQ_LINK_DOMINIOS` | vazio | Domínios que recebem o `?ceq=` no modo `parametro`, separados por vírgula (ex.: `ia-thefuture.vercel.app`). Vazio: nenhum link muda. Também são as únicas origens aceitas no aviso de abertura. |
| `CEQ_RECONSULTA_HORAS` | `24` | De quanto em quanto tempo reconferir quem segue a conta. `0` desliga. |
| `CEQ_RECONSULTA_TAGS` | `isca_viral` | Só reconfere leads com uma destas etiquetas (vírgula separa). `*` = todos que constam como seguidores. |
| `CEQ_RECONSULTA_MAX` | `150` | Máximo de perfis por rodada. |
| `CEQ_RECONSULTA_INTERVALO_S` | `3` | Segundos entre uma consulta e outra. |

## Retenção de dados

| Variável | Padrão | Para quê |
|---|---|---|
| `RETENCAO_LEADS_DIAS` | vazio (guarda tudo) | Apaga o lead parado há mais que esse número de dias, com etiquetas e campos. Roda uma vez por dia. |
| `RETENCAO_EVENTOS_DIAS` | vazio (guarda tudo) | Apaga o histórico técnico mais velho que isso. |

## Alertas

| Variável | Padrão | Para quê |
|---|---|---|
| `ALERTA_TELEGRAM_TOKEN` | vazio | Token de um bot do Telegram que avisa quando a Meta segura os envios. O que for salvo em Configurações vale mais. |
| `ALERTA_TELEGRAM_CHAT` | vazio | O seu ID no Telegram (o @userinfobot informa). |

## Segurança e acesso

| Variável | Padrão | Para quê |
|---|---|---|
| `CEQ_LOGIN_FALHAS_JANELA` | `30` | Senhas erradas, somando todos os IPs, aceitas em 10 minutos antes de travar o login. |
| `CEQ_PERMITE_HTTP` | vazio | `1` libera o login por HTTP. Só para proxy que não envia `X-Forwarded-Proto`. Não use sem necessidade. |
| `CEQ_SETUP_TOKEN` | vazio | Usado pelo instalador: libera a página `/instalar?t=` para criar a senha no primeiro acesso. |
| `CEQ_MCP_REDIRECTS` | vazio | Hosts extras (separados por vírgula) pra onde o login OAuth do conector MCP pode devolver o acesso. Por padrão só `claude.ai`, `claude.com` e `localhost`. Ver [MCP](./mcp.md). |

## Instalação

| Variável | Padrão | Para quê |
|---|---|---|
| `DATA_DIR` | `/data` na imagem | Pasta do banco (`comentaeuquero.db`) e das fotos de perfil. |

## WhatsApp

As credenciais do WhatsApp (WABA ID, Phone Number ID e token permanente) entram pelo painel e ficam cifradas com a `CEQ_ENCRYPTION_KEY`. Se o canal ganhar variáveis próprias no lançamento, elas entram nesta página.
