"""Link mágico (1.17.0): link do funil pra material do ia_thefuture sai assinado
pra pessoa. O site confere com o mesmo segredo e libera só aquele item."""
import hashlib
import hmac
import time
import uuid
from urllib.parse import parse_qs, urlsplit

import pytest

from app import db, instagram, links, runtime

DESTINO = "https://ia-thefuture.vercel.app/#item-tut-clonar-viral"
SEGREDO = "s3gr3do-de-teste-com-32-caracteres!!"


@pytest.fixture
def ig(monkeypatch):
    monkeypatch.setattr(runtime, "THROTTLE_S", 0)
    monkeypatch.setattr(runtime, "LIMITER", runtime.RateLimiter(1000))
    db.set_ajuste("throttle_until", "")
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    monkeypatch.setenv("LINK_MAGICO_SEGREDO", SEGREDO)
    enviados = []
    monkeypatch.setattr(instagram, "send_text",
                        lambda a, r, t, *x, **k: enviados.append(t) or (True, "", {}))
    monkeypatch.setattr(instagram, "fetch_profile", lambda *a, **k: {})
    acc = db.upsert_account(uuid.uuid4().hex, "", "conta_ig", "tok", "2099-01-01T00:00:00Z")
    db.conn().execute("DELETE FROM accounts WHERE id<>?", (acc["id"],)); db.conn().commit()
    return db.get_account(acc["id"]), enviados


def _envia(acc, igsid, username):
    f = db.create_flow(acc["id"], name="Isca VIRAL", entry_node="n0", graph={
        "nodes": [{"id": "n0", "type": "text", "data": {"text": "Tá aqui", "link": DESTINO}}],
        "edges": []})
    lead = db.touch_lead(acc["id"], igsid, "", username)
    db.abrir_janela(lead["id"], "ig")
    runtime.start(acc, db.get_flow(f), lead)
    return lead


def _link(texto):
    return next(p for p in texto.split() if p.startswith("https://"))


def _confere_como_o_site(url, segredo=SEGREDO):
    """O que o ia_thefuture faz do lado dele."""
    p = urlsplit(url)
    q = parse_qs(p.query)
    token, (expira, sig) = q["ceq"][0], q["mg"][0].split(".")
    item = p.fragment.removeprefix("item-")
    certo = hmac.new(segredo.encode(), f"{token}.{item}.{expira}".encode(),
                     hashlib.sha256).hexdigest()
    return hmac.compare_digest(certo, sig) and int(expira) > time.time(), token, item


def test_link_sai_assinado_e_o_site_confere(ig):
    acc, env = ig
    _envia(acc, "1", "maria")
    url = _link(env[-1])
    assert url.startswith("https://ia-thefuture.vercel.app/?ceq=") and "&mg=" in url
    assert url.endswith("#item-tut-clonar-viral")
    ok, token, item = _confere_como_o_site(url)
    assert ok and item == "tut-clonar-viral"
    assert db.link_por_token(token)["url"] == DESTINO


def test_cada_pessoa_tem_o_seu(ig):
    acc, env = ig
    _envia(acc, "1", "maria"); a = _link(env[-1])
    _envia(acc, "2", "joao"); b = _link(env[-1])
    assert parse_qs(urlsplit(a).query)["ceq"] != parse_qs(urlsplit(b).query)["ceq"]


def test_trocar_item_ou_token_invalida(ig):
    acc, env = ig
    _envia(acc, "1", "maria")
    url = _link(env[-1])
    assert not _confere_como_o_site(url.replace("#item-tut-clonar-viral", "#item-outro"))[0]
    outro = url.replace("ceq=", "ceq=X", 1)
    assert not _confere_como_o_site(outro)[0]
    assert not _confere_como_o_site(url, segredo="outro-segredo")[0]


def test_expira(monkeypatch):
    monkeypatch.setenv("LINK_MAGICO_SEGREDO", SEGREDO)
    monkeypatch.setenv("LINK_MAGICO_DIAS", "30")
    url = links.com_magico(links.com_parametro(DESTINO, "TOKEN12345"), "TOKEN12345",
                           agora=time.time() - 31 * 86400)
    assert not _confere_como_o_site(url)[0]


def test_sem_segredo_ou_sem_item_nao_assina(ig, monkeypatch):
    acc, env = ig
    monkeypatch.delenv("LINK_MAGICO_SEGREDO")
    _envia(acc, "1", "maria")
    assert "mg=" not in _link(env[-1]) and "ceq=" in _link(env[-1])
    monkeypatch.setenv("LINK_MAGICO_SEGREDO", SEGREDO)
    assert links.com_magico("https://ia-thefuture.vercel.app/?ceq=T", "T") == \
        "https://ia-thefuture.vercel.app/?ceq=T"


def test_busca_de_leads_acha_pelo_codigo_do_link(ig):
    acc, env = ig
    _envia(acc, "1", "maria")
    _envia(acc, "2", "joao")
    token = parse_qs(urlsplit(_link(env[-1])).query)["ceq"][0]
    assert [l["username"] for l in db.list_leads(acc["id"], busca=token)] == ["joao"]


def test_redirecionar_tambem_entrega_assinado(client, ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_RASTREADO", "redirecionar")
    monkeypatch.setenv("BASE_URL", "https://ceq.exemplo.com")
    _envia(acc, "1", "redir.magico")      # nome próprio: o clique fica no banco comum
    token = _link(env[-1]).split("/r/")[1]
    r = client.get(f"/r/{token}", headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=False)
    assert r.status_code == 302 and _confere_como_o_site(r.headers["location"])[0]
