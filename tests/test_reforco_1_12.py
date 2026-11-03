"""Reforços de segurança da 1.12.0: cabeçalhos, checagem de origem e nó de webhook."""
from fastapi.testclient import TestClient

from app import main, runtime


def _cliente():
    return TestClient(main.app)


def test_cabecalhos_de_seguranca():
    r = _cliente().get("/privacy")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "same-origin"


def test_post_com_cookie_vindo_de_outro_site_e_barrado():
    c = _cliente()
    c.cookies.set("ceq_session", "qualquer")
    r = c.post("/logout-todos", headers={"Origin": "https://site-malicioso.com"})
    assert r.status_code == 403
    r = c.post("/logout-todos", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403


def test_post_com_cookie_do_proprio_site_passa():
    c = _cliente()
    c.cookies.set("ceq_session", "qualquer")
    r = c.post("/logout-todos", headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert r.status_code != 403


def test_post_sem_cookie_nao_e_afetado():
    # webhook da Meta e MCP com Bearer não mandam cookie
    r = _cliente().post("/webhook", content=b"{}", headers={"Origin": "https://outro.com"})
    assert r.status_code != 403 or r.text != "origem não permitida"


def test_webhook_do_fluxo_recusa_esquema_estranho(monkeypatch):
    chamou = []
    monkeypatch.setattr(runtime.requests, "post", lambda *a, **k: chamou.append(k))
    out = runtime._chama_webhook({"url": "file:///etc/passwd"}, {"id": 1}, {})
    assert "erro" in out and not chamou


def test_webhook_do_fluxo_limita_o_prazo(monkeypatch):
    vistos = []

    class R:
        status_code = 204
        headers = {}

    def falso(url, json=None, timeout=None):
        vistos.append(timeout)
        return R()
    monkeypatch.setattr(runtime.requests, "post", falso)
    monkeypatch.setattr(runtime.db, "lead_fields", lambda _id: {})
    monkeypatch.setattr(runtime.db, "lead_tags", lambda _id: [])
    for pedido, esperado in ((None, 15.0), (0.001, 1.0), (9999, 30.0), ("x", 15.0)):
        runtime._chama_webhook({"url": "https://exemplo.com", "timeout": pedido}, {"id": 1}, {})
        assert vistos[-1] == esperado
