# Changelog

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

Primeira versão deste repositório (cadubezerrapro/comentaeuquero), derivada do
comenta EU QUERO 1.11.2 de Augusto Gobatto (Licença de Uso Sustentável 1.0).

- Removida a ativação por `CLUB_TOKEN`: a instância não manda mais ping, versão,
  contagem de leads nem id de instalação para nenhum servidor externo. As únicas
  saídas de rede são Meta, Anthropic (se o nó de IA estiver ligado) e Telegram (se
  o alerta estiver configurado).
- Removidos `CLUB_TOKEN`, `ACTIVATION_URL`, `CHAO_URL` e `CHAO_VERSAO`, o aviso de
  assinatura no painel e o campo `licenca` do `/health` e do MCP.
- Removidos o `docker-compose.club.yml` (watchtower apontando para a imagem do
  autor original), o site de divulgação e o script de exportação interno.
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
