"""Ponta a ponta pelo HTTP, como vai rodar na VPS.

Sobe o app de verdade (TestClient, rotas, middleware, webhook assinado, tarefa em
segundo plano, motor de fluxo, banco) e dubla SÓ a rede da Meta: cada chamada que
sairia pra graph.instagram.com fica anotada aqui. Cobre o caminho que importa pro
dono da conta:

  primeiro acesso -> login -> fluxo com palavra-chave -> alguém comenta -> DM sai
  por private reply + resposta pública -> lead registrado com origem e palavra ->
  pessoa responde com e-mail -> campo salvo -> métricas e CSV contam tudo certo,
  e as portas que precisam ficar fechadas (assinatura, origem, conta própria).
"""
import hashlib
import hmac
import json
import os
import re
import shutil
import sys

DATA = "/tmp/ceq_e2e"
shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA)
os.environ.update({
    "DATA_DIR": DATA,
    "META_APP_ID": "123",
    "META_APP_SECRET": "segredo-do-app",
    "WEBHOOK_VERIFY_TOKEN": "verifica-xyz",
    "BASE_URL": "https://ceq.exemplo.com.br",
    "ADMIN_PASSWORD": "",
    "CEQ_SETUP_TOKEN": "setup-abc",
})
for v in ("META_LOGIN_MODO", "META_FB_APP_ID", "META_FB_APP_SECRET", "CEQ_PERMITE_HTTP"):
    os.environ.pop(v, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient  # noqa: E402

from app import db, instagram, runtime  # noqa: E402

falhas = []


def check(nome, cond, detalhe=""):
    print(f"  {'OK ' if cond else 'FALHOU'}  {nome}{'  ' + str(detalhe) if detalhe else ''}")
    if not cond:
        falhas.append(nome)


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.headers = {"content-type": "application/json"}
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


CHAMADAS = []


def _meta(metodo):
    def f(url, params=None, json=None, data=None, headers=None, timeout=None, **kw):
        CHAMADAS.append({"metodo": metodo, "url": url, "corpo": json if json is not None else data,
                         "params": params or {}})
        if metodo == "POST" and url.endswith("/messages"):
            return _Resp(200, {"recipient_id": "x", "message_id": f"mid.{len(CHAMADAS)}"})
        if metodo == "POST" and url.endswith("/replies"):
            return _Resp(200, {"id": f"reply{len(CHAMADAS)}"})
        if metodo == "GET":
            return _Resp(200, {"username": "fulana", "name": "Fulana Silva",
                               "is_user_follow_business": True, "follower_count": 10})
        return _Resp(200, {"success": True})
    return f


instagram.requests.get = _meta("GET")
instagram.requests.post = _meta("POST")
runtime.THROTTLE_S = 0

db.init()
from app import main  # noqa: E402

c = TestClient(main.app, base_url="https://ceq.exemplo.com.br")
ORIGEM = {"Origin": "https://ceq.exemplo.com.br"}


def assina(corpo: bytes, segredo="segredo-do-app"):
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


def webhook(payload, segredo="segredo-do-app", assinar=True):
    corpo = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if assinar:
        h["X-Hub-Signature-256"] = assina(corpo, segredo)
    return c.post("/webhook", content=corpo, headers=h)


print("\n[1] primeiro acesso e login")
check("/instalar sem token some (404)", c.get("/instalar").status_code == 404)
r = c.get("/instalar?t=setup-abc")
check("/instalar com token abre", r.status_code == 200, r.status_code)
r = c.post("/instalar?t=setup-abc", data={"t": "setup-abc", "senha": "SenhaForte#2026",
                                           "confirma": "SenhaForte#2026",
                                           "senha2": "SenhaForte#2026"},
           headers=ORIGEM, follow_redirects=False)
check("senha criada", db.get_ajuste("admin_senha_hash") not in (None, ""), r.status_code)
check("/instalar fecha depois da senha", c.get("/instalar?t=setup-abc").status_code == 404)
c.cookies.clear()
r = c.post("/login", data={"senha": "errada"}, headers=ORIGEM, follow_redirects=False)
check("senha errada não entra", "ceq_session" not in r.cookies, r.status_code)
r = c.post("/login", data={"senha": "SenhaForte#2026"}, headers=ORIGEM, follow_redirects=False)
check("senha certa entra", r.status_code in (302, 303) and "ceq_session" in c.cookies, r.status_code)
for pagina in ("/painel", "/fluxos", "/leads", "/config", "/editor"):
    r = c.get(pagina, follow_redirects=False)
    check(f"{pagina} abre logado", r.status_code == 200, r.status_code)

print("\n[2] verificação do webhook pela Meta")
r = c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verifica-xyz",
                              "hub.challenge": "42"})
check("token certo devolve o challenge", r.status_code == 200 and r.text == "42", r.text)
r = c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "errado",
                              "hub.challenge": "42"})
check("token errado é recusado", r.status_code == 403, r.status_code)

print("\n[3] conta conectada + fluxo com palavra-chave")
# simula o fim do OAuth: a conta entra no banco como entraria pelo /auth/callback
conta = db.upsert_account("IGACC", "17841400000000001", "minhaloja", "IGTOKEN",
                          db.in_seconds_iso(86400 * 60))
fid = db.create_flow(conta["id"], "ebook", entry_node="n1", graph={
    "nodes": [{"id": "n1", "type": "text", "data": {"text": "Oi {username}! Aqui está:",
                                                   "link": "https://loja.com/ebook"}},
              # como o editor monta: a pergunta é uma mensagem, o nó seguinte espera
              {"id": "n2", "type": "text", "data": {"text": "Me passa teu melhor e-mail?"}},
              {"id": "n3", "type": "wait_input", "data": {
                  "expects": "email", "save_as": "email",
                  "retry_text": "Esse e-mail não parece certo"}},
              {"id": "n4", "type": "text", "data": {"text": "Valeu! Mando no {email}"}}],
    "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n3"},
              {"source": "n3", "target": "n4"}]})
db.add_trigger(fid, "comment", ["ebook"], public_reply="Te mandei no direct!")
check("fluxo ativo", db.get_flow(fid)["active"] == 1)


def comentario(texto, cid, uid="U1", user="fulana"):
    return {"object": "instagram", "entry": [{"id": "IGACC", "time": 1, "changes": [{
        "field": "comments", "value": {"id": cid, "text": texto, "media": {"id": "M1"},
                                       "from": {"id": uid, "username": user}}}]}]}


def dm(texto, uid="U1", mid="m1"):
    return {"object": "instagram", "entry": [{"id": "IGACC", "time": 2, "messaging": [{
        "sender": {"id": uid}, "recipient": {"id": "IGACC"},
        "message": {"mid": mid, "text": texto}}]}]}


print("\n[4] portas fechadas no webhook")
CHAMADAS.clear()
check("sem assinatura: 403", webhook(comentario("EBOOK", "cA"), assinar=False).status_code == 403)
check("assinatura de outro: 403", webhook(comentario("EBOOK", "cB"), segredo="x").status_code == 403)
check("nada foi enviado", not CHAMADAS, len(CHAMADAS))

print("\n[5] alguém comenta a palavra-chave")
CHAMADAS.clear()
r = webhook(comentario("Quero o EBOOK por favor!", "C1"))
check("webhook aceita (200)", r.status_code == 200, r.status_code)
msgs = [x for x in CHAMADAS if x["url"].endswith("/messages")]
publicas = [x for x in CHAMADAS if x["url"].endswith("/replies")]
check("1ª DM saiu por private reply", msgs and msgs[0]["corpo"]["recipient"] == {"comment_id": "C1"},
      msgs[:1])
check("texto com nome e link", msgs and "fulana" in msgs[0]["corpo"]["message"]["text"]
      and "https://loja.com/ebook" in msgs[0]["corpo"]["message"]["text"],
      msgs and msgs[0]["corpo"]["message"]["text"])
check("pediu o e-mail", len(msgs) == 2 and "e-mail" in json.dumps(msgs[1]["corpo"], ensure_ascii=False),
      len(msgs))
check("2ª mensagem já vai pelo direct (id)", len(msgs) == 2 and msgs[1]["corpo"]["recipient"] == {"id": "U1"})
check("respondeu em público no comentário", len(publicas) == 1 and "C1" in publicas[0]["url"])
lead = db.conn().execute("select * from leads where igsid='U1'").fetchone()
check("lead registrado", lead is not None)
check("lead com @ e palavra-chave", lead and lead["username"] == "fulana"
      and (lead["last_keyword"] or "").lower() == "ebook", dict(lead) if lead else None)

print("\n[6] mesmo comentário entregue 2x pela Meta não duplica")
CHAMADAS.clear()
webhook(comentario("Quero o EBOOK por favor!", "C1"))
check("não reenviou", not [x for x in CHAMADAS if x["url"].endswith("/messages")], len(CHAMADAS))

print("\n[7] a pessoa responde no direct")
CHAMADAS.clear()
webhook(dm("sei la", mid="m1"))
check("e-mail inválido: pede de novo", any("não parece certo" in json.dumps(x["corpo"], ensure_ascii=False)
                                          for x in CHAMADAS))
check("campo não salvo ainda", db.get_field(lead["id"], "email") == "")
CHAMADAS.clear()
webhook(dm("é fulana@Email.com", mid="m2"))
check("e-mail salvo normalizado", db.get_field(lead["id"], "email") == "fulana@email.com",
      db.get_field(lead["id"], "email"))
check("agradeceu com o e-mail", any("fulana@email.com" in json.dumps(x["corpo"])
                                     for x in CHAMADAS))

print("\n[8] comentário da própria conta e sem palavra-chave")
CHAMADAS.clear()
webhook(comentario("ebook", "C2", uid="17841400000000001", user="minhaloja"))
webhook(comentario("que lindo", "C3", uid="U9", user="outra"))
check("não respondeu a si mesmo nem a quem não pediu",
      not [x for x in CHAMADAS if x["url"].endswith("/messages")], len(CHAMADAS))

print("\n[9] métricas e exportação")
st = db.stats()
# entregas: 1ª DM, pergunta e agradecimento (o aviso de e-mail inválido não conta)
check("contou as 3 entregas", st.get("total") == 3, st.get("total"))
check("nenhuma falha de envio", st.get("fails") == 0, st.get("fails"))
r = c.get("/api/export.csv?tipo=leads", follow_redirects=False)
check("CSV de leads baixa", r.status_code == 200, r.status_code)
check("CSV tem o lead e o e-mail", "fulana" in r.text and "fulana@email.com" in r.text,
      r.text[:200])
r = c.get("/health")
check("/health logado mostra conta e versão",
      r.json().get("username") == "minhaloja" and r.json().get("versao"), r.json())
r = c.get("/painel")
check("painel abre com a conta", r.status_code == 200 and "minhaloja" in r.text)

print("\n[10] proteções do painel")
r = c.post("/logout-todos", headers={"Origin": "https://site-malicioso.com"}, follow_redirects=False)
check("POST de outro site com cookie: 403", r.status_code == 403, r.status_code)
c2 = TestClient(main.app, base_url="https://ceq.exemplo.com.br")
check("sem login não vê leads", c2.get("/leads", follow_redirects=False).status_code in (302, 303, 401))
check("sem login /health não vaza dados", set(c2.get("/health").json()) <= {"ok", "conta_conectada"})
check("tokens não aparecem no CSV", "IGTOKEN" not in c.get("/api/export.csv?tipo=leads").text)
check("tokens não aparecem no painel", "IGTOKEN" not in c.get("/config").text)

print()
if falhas:
    print(f"FALHAS ({len(falhas)}): " + "; ".join(falhas))
    sys.exit(1)
print("ponta a ponta: tudo OK")
