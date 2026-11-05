# comenta EU QUERO

[![License](https://img.shields.io/badge/license-Sustainable%20Use%201.0-blue)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](requirements.txt)
[![Docker Image](https://github.com/cadubezerrapro/comentaeuquero/actions/workflows/imagem.yml/badge.svg)](https://github.com/cadubezerrapro/comentaeuquero/actions/workflows/imagem.yml)
[![Tests](https://github.com/cadubezerrapro/comentaeuquero/actions/workflows/testes.yml/badge.svg)](https://github.com/cadubezerrapro/comentaeuquero/actions/workflows/testes.yml)
[![Release](https://img.shields.io/github/v/release/cadubezerrapro/comentaeuquero)](https://github.com/cadubezerrapro/comentaeuquero/releases)

Automação de comentários no Instagram: a pessoa comenta **EU QUERO** (ou a palavra que você definir) e recebe o link no direct. Painel, editor de fluxos visual e deploy com Docker — no seu próprio servidor, com seu próprio app da Meta, sem mensalidade e sem limite de contatos.

[Documentação](docs/) · [Changelog](CHANGELOG.md) · [Reportar um bug](https://github.com/cadubezerrapro/comentaeuquero/issues)

---

## Recursos

- **Gatilhos no Instagram** — comentários em posts e lives, respostas de story e DMs
- **Editor de fluxos visual** — mensagens, botões, condições, captura de lead, tags, webhooks e respostas por IA
- **Gestão de leads** — exportação em CSV, filtros por palavra-chave e por origem
- **Segurança e limites** — cap de envios por hora, fila com rate-limit, webhooks assinados, retenção de dados configurável
- **WhatsApp (opcional)** — via Cloud API oficial da Meta, com os mesmos fluxos, templates e broadcasts com relatório
- **Integração MCP** — servidor MCP em `/mcp`, pra gerenciar a instância conversando com o Claude ou outro client MCP

## Instalação rápida

Pré-requisitos: conta profissional do Instagram, Docker e um endpoint HTTPS público.

```bash
git clone https://github.com/cadubezerrapro/comentaeuquero.git
cd comentaeuquero
cp .env.example .env   # preencha com suas credenciais
docker compose up -d
```

Tutoriais passo a passo estão em [`docs/`](docs/).

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `META_APP_ID` | Sim | ID do app da Meta usado para a integração |
| `META_APP_SECRET` | Sim | Secret do app da Meta |
| `WEBHOOK_VERIFY_TOKEN` | Sim | Token de verificação do webhook do Instagram |
| `DATABASE_URL` | Não | Caminho do banco SQLite (padrão interno se omitido) |
| `WHATSAPP_*` | Não | Credenciais da Cloud API, apenas se usar o módulo de WhatsApp |

Veja o arquivo [`.env.example`](.env.example) para a lista completa.

## Stack

Python 3.12 · FastAPI · SQLite · Vue 3 (Vue Flow) · Docker · imagens assinadas com cosign

## Licença

Distribuído sob a [Sustainable Use License 1.0](LICENSE.md). Você pode usar, modificar e instalar para clientes — não pode hospedar e revender como serviço (SaaS).

Projeto mantido por **Cadu Bezerra** ([@cadubezerrapro](https://github.com/cadubezerrapro)).

## Contribuindo

Issues e PRs são bem-vindos. Sugestões de feature usam a label `sugestao`. Para reportar vulnerabilidades, siga [SECURITY.md](SECURITY.md).
