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
import hashlib
import hmac
import os
import re
import time
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


# ---------- link mágico (1.17.0) ----------
# Link do funil pra um material do ia_thefuture (`#item-<id>`) sai assinado pra
# pessoa que pediu: ?ceq=<token>&mg=<expira>.<assinatura>. O site confere a
# assinatura com o mesmo segredo e libera SÓ aquele item, sem login, até expirar.
# O resto do site continua pedindo cadastro. Sem o segredo, nada muda.
RE_ITEM = re.compile(r"^item-([A-Za-z0-9_-]{1,80})$")
PARAMETRO_MAGICO = "mg"


def segredo_magico() -> str:
    return (os.environ.get("LINK_MAGICO_SEGREDO", "") or "").strip()


def dias_magico() -> int:
    try:
        return max(1, int(os.environ.get("LINK_MAGICO_DIAS", "") or 30))
    except ValueError:
        return 30


def item_do_link(url) -> str:
    m = RE_ITEM.match(urlsplit(url).fragment or "")
    return m.group(1) if m else ""


def assinatura_magica(token, item, expira, segredo=None) -> str:
    """HMAC-SHA256 de "<token>.<item>.<expira>" em hex. O ia_thefuture calcula igual."""
    chave = (segredo if segredo is not None else segredo_magico()).encode()
    return hmac.new(chave, f"{token}.{item}.{expira}".encode(), hashlib.sha256).hexdigest()


def com_magico(url, token, agora=None) -> str:
    """Acrescenta mg=<expira>.<assinatura> ao link que já tem ?ceq=<token>. Só pra
    material (#item-...) e com segredo configurado; senão devolve igual."""
    item, segredo = item_do_link(url), segredo_magico()
    if not item or not segredo or not token:
        return url
    expira = int((agora or time.time()) + dias_magico() * 86400)
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k != PARAMETRO_MAGICO]
    query.append((PARAMETRO_MAGICO, f"{expira}.{assinatura_magica(token, item, expira, segredo)}"))
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
        token = db.token_link(account_id, lead["id"], flow_name, node_id, url)
        return com_magico(com_parametro(url, token), token)
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
