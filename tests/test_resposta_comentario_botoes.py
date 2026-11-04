"""Comentário -> texto -> botões: a Meta aceita só UMA private reply (04/11/2026).

Caso real: o fluxo mandou o texto por private reply e os botões em seguida; a Meta
recusou os botões com code 10 / subcode 2534022 ("fora da janela permitida"). O
motor agora manda o texto como corpo da mensagem de botões, numa mensagem só.
"""
import uuid

import pytest

from app import db, instagram, runtime


@pytest.fixture(autouse=True)
def _sem_throttle(monkeypatch):
    monkeypatch.setattr(runtime, "THROTTLE_S", 0)
    monkeypatch.setattr(runtime, "LIMITER", runtime.RateLimiter(1000))


@pytest.fixture
def ig(monkeypatch):
    enviados = []

    def _ok(nome):
        def f(account, recipient, texto, *a, **k):
            enviados.append((nome, recipient, texto))
            return True, 200, {}
        return f
    monkeypatch.setattr(instagram, "send_text", _ok("texto"))
    monkeypatch.setattr(instagram, "send_buttons", _ok("botoes"))
    monkeypatch.setattr(instagram, "send_quick_replies", _ok("quick"))
    monkeypatch.setattr(instagram, "fetch_profile", lambda *a, **k: None)
    acc = db.upsert_account(uuid.uuid4().hex, "", "conta_ig", "tok-ig", "2099-01-01T00:00:00Z")
    db.conn().execute("DELETE FROM accounts WHERE id<>?", (acc["id"],)); db.conn().commit()
    return db.get_account(acc["id"]), enviados


def _grafo(tipo="buttons", texto="Oi {first_name}! Tá aqui"):
    if tipo == "buttons":
        b = {"id": "n_b", "type": "buttons", "data": {
            "text": "Quer o link?", "buttons": [{"title": "Quero", "key": "quero"}]}}
    else:
        b = {"id": "n_b", "type": "quick_replies", "data": {
            "text": "Quer o link?", "options": [{"title": "Quero", "key": "quero"}]}}
    return {"nodes": [
        {"id": "n0", "type": "text", "data": {"text": texto}}, b,
        {"id": "n_fim", "type": "text", "data": {"text": "aqui o link"}}],
        "edges": [{"id": "a", "source": "n0", "target": "n_b"},
                  {"id": "b", "source": "n_b", "target": "n_fim", "sourceHandle": "quero"}]}


def _inicia(acc, grafo, igsid, comment_id):
    f = db.create_flow(acc["id"], name="TESTE", graph=grafo, entry_node="n0")
    lead = db.touch_lead(acc["id"], igsid, "", "zuckpay")
    motivo = runtime.start(acc, db.get_flow(f), lead, comment_id=comment_id)
    return motivo, db.get_lead(lead["id"])


@pytest.mark.parametrize("tipo,nome", [("buttons", "botoes"), ("quick_replies", "quick")])
def test_comentario_texto_e_botoes_vao_numa_mensagem_so(ig, tipo, nome):
    acc, enviados = ig
    motivo, lead = _inicia(acc, _grafo(tipo), "ig-" + tipo, "c-" + tipo)
    assert motivo == "esperando_clique"
    assert len(enviados) == 1
    qual, recipient, texto = enviados[0]
    assert qual == nome and recipient == {"comment_id": "c-" + tipo}
    assert texto.startswith("Oi") and texto.endswith("Quer o link?")
    s = db.active_session_for_lead(lead["id"])
    assert s["node_id"] == "n_b" and s["waiting_for"] == "postback"
    runtime.resume_postback(acc, lead, "quero")
    assert enviados[-1][0] == "texto" and enviados[-1][2] == "aqui o link"


def test_sem_comentario_continua_em_duas_mensagens(ig):
    acc, enviados = ig
    f = db.create_flow(acc["id"], name="DM", graph=_grafo(), entry_node="n0")
    lead = db.touch_lead(acc["id"], "ig-dm", "", "zuckpay")
    db.abrir_janela(lead["id"], "ig")
    runtime.start(acc, db.get_flow(f), lead)
    assert [e[0] for e in enviados] == ["texto", "botoes"]


def test_texto_grande_demais_nao_junta(ig):
    acc, enviados = ig
    _inicia(acc, _grafo(texto="x" * 700), "ig-grande", "c-grande")
    assert enviados[0][0] == "texto"
