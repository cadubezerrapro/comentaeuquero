"""Link rastreado (1.15.0): saber quem abriu o link que o fluxo mandou.

A Meta não avisa clique em link de DM. Dois jeitos de medir, escolhidos por
CEQ_LINK_RASTREADO:

- "parametro" (padrão): o link continua sendo o endereço real do destino, só ganha
  ?ceq=<token> (como um UTM). Quem registra o clique é o próprio site de destino, que
  chama POST /r/<token>/visto quando a página abre (snippet em docs/link-rastreado.md).
  Só vale pros domínios listados em CEQ_LINK_DOMINIOS (os seus sites, que sabem
  avisar): link pra qualquer outro domínio sai intocado.

- "redirecionar": o link vira BASE_URL/r/<token> e a rota redireciona (302) pro
  destino. Funciona com qualquer site, mas é o formato que os filtros da Meta olham
  com desconfiança (link que manda pra outro domínio). Só ligue sabendo disso, de
  preferência com BASE_URL num domínio próprio, não num subdomínio compartilhado.

- "desligado": nada muda.

Por que o padrão é "parametro": a política de spam da Meta trata como suspeito link
que leva a um domínio diferente do que aparece, e subdomínio de hospedagem
compartilhada (railway.app, vercel.app) já tem reputação baixa nos classificadores.
Com o parâmetro, o domínio que a pessoa vê é exatamente o que ela abre.

Regras que valem nos dois modos:
- Nunca cloaking: robô de prévia (o da Meta, o do WhatsApp) recebe o MESMO destino que
  a pessoa. Ele só não conta como clique.
- O token é aleatório e não leva dado do lead.
"""
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import db

MODOS = ("parametro", "redirecionar", "desligado")
PARAMETRO = "ceq"
RE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{8,32}$")

# Quem busca o link pra montar a prévia, não é a pessoa. Lista conservadora: só
# deixa de CONTAR, o destino entregue é o mesmo.
ROBOS = ("facebookexternalhit", "facebot", "meta-externalagent", "meta-externalfetcher",
         "whatsapp", "instagram link preview", "twitterbot", "slackbot", "telegrambot",
         "discordbot", "linkedinbot", "googlebot", "bingbot", "applebot", "skypeuripreview",
         "embedly", "preview", "crawler", "spider", "curl/", "python-requests", "wget/")


def modo() -> str:
    m = (os.environ.get("CEQ_LINK_RASTREADO", "") or "parametro").strip().lower()
    return m if m in MODOS else "parametro"


def dominios() -> set:
    """Domínios (host) que recebem o parâmetro. Subdomínio conta: 'site.com' cobre
    'www.site.com'."""
    return {d.strip().lower().lstrip(".") for d in
            os.environ.get("CEQ_LINK_DOMINIOS", "").split(",") if d.strip()}


def _host(url) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def dominio_liberado(url) -> bool:
    host = _host(url)
    return bool(host) and any(host == d or host.endswith("." + d) for d in dominios())


def _base_url() -> str:
    return os.environ.get("BASE_URL", "").rstrip("/")


def com_parametro(url, token) -> str:
    """url + ?ceq=token, preservando query e #âncora (o ia_thefuture navega por #)."""
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != PARAMETRO]
    query.append((PARAMETRO, token))
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query), p.fragment))


def rastrear(url, account_id, lead, flow_name, node_id) -> str:
    """O link que vai na mensagem. Devolve a própria url quando não há o que rastrear."""
    url = (url or "").strip()
    if not url or not lead or not lead.get("id"):
        return url
    if not url.lower().startswith(("https://", "http://")):
        return url
    m = modo()
    if m == "desligado":
        return url
    base = _base_url()
    if base and url.startswith(base + "/r/"):
        return url                       # já é um link rastreado
    if m == "parametro":
        if not dominio_liberado(url):
            return url
        return com_parametro(url, db.token_link(account_id, lead["id"], flow_name, node_id, url))
    # redirecionar
    if not base.startswith("https://"):
        return url                       # sem domínio público https, não tem pra onde
    return f"{base}/r/{db.token_link(account_id, lead['id'], flow_name, node_id, url)}"


def e_robo(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return not ua or any(r in ua for r in ROBOS)


def origem_permitida(origin: str) -> bool:
    """O aviso de 'visto' só é aceito vindo dos domínios configurados."""
    host = _host(origin or "")
    return bool(host) and any(host == d or host.endswith("." + d) for d in dominios())
