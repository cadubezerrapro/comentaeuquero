# Changelog

## 1.12.0 (2026-11-03)

Primeira versão deste repositório (cadubezerrapro/comentaeuquero), derivada do
comenta EU QUERO 1.11.2 de Cadu Bezerra (Licença de Uso Sustentável 1.0).

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
