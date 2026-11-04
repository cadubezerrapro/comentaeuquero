"""Logs do sistema (1.13.0): erro real da Meta no evento de envio e a página /logs."""
import json

from fastapi.testclient import TestClient

from app import db, instagram, main, runtime


def _cliente_logado(monkeypatch):
    monkeypatch.setattr(main, "logged_in", lambda request: True)
    monkeypatch.setattr(main, "require_login", lambda request: None)
    return TestClient(main.app)


def test_resumo_erro_da_meta():
    corpo = {"error": {"message": "(#10) Application does not have permission",
                       "type": "OAuthException", "code": 10, "error_subcode": 2534022}}
    r = instagram.resumo_erro(400, corpo)
    assert "http 400" in r and "code 10" in r and "subcode 2534022" in r
    assert "Application does not have permission" in r


def test_resumo_erro_sem_json_nao_vaza_token():
    r = instagram.resumo_erro(0, "erro em https://x/?access_token=SEGREDO123&y=1")
    assert "SEGREDO123" not in r


def test_falha_de_envio_guarda_o_motivo(monkeypatch):
    corpo = {"error": {"message": "User consent is required", "code": 551, "error_subcode": 1545041}}
    monkeypatch.setattr(instagram, "send_text", lambda *a, **k: (False, 400, corpo))
    monkeypatch.setattr(runtime.LIMITER, "tenta", lambda: True)
    monkeypatch.setattr(instagram, "cooldown_restante", lambda: 0)
    ok, det = runtime._enviar({"id": 1}, {"context": {}}, {"id": "n1", "type": "text",
                                                          "data": {"text": "oi"}},
                              {"id": 1, "username": "x"}, {"id": "U1"})
    assert ok is False
    assert "erro da Meta" in det and "code 551" in det and "User consent is required" in det


def test_envio_ok_nao_ganha_sufixo(monkeypatch):
    monkeypatch.setattr(instagram, "send_text", lambda *a, **k: (True, 200, {"message_id": "m"}))
    monkeypatch.setattr(runtime.LIMITER, "tenta", lambda: True)
    monkeypatch.setattr(instagram, "cooldown_restante", lambda: 0)
    ok, det = runtime._enviar({"id": 1}, {"context": {}}, {"id": "n1", "type": "text",
                                                          "data": {"text": "oi"}},
                              {"id": 1, "username": "x"}, {"id": "U1"})
    assert ok is True and "erro" not in det


def test_logs_exige_login():
    r = TestClient(main.app).get("/logs", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_logs_lista_filtra_e_destaca_erro(monkeypatch):
    c = _cliente_logado(monkeypatch)
    db.log_event("fluxo_envio", None, "Fluxo X", "text", False, "fulana",
                 {"node": "n1", "detalhe": "oi | erro da Meta: http 400 · code 10: sem permissão"})
    db.log_event("webhook", None, "", "", None, "", {"resumo": ["comments"]})
    r = c.get("/logs")
    assert r.status_code == 200
    assert "Logs do sistema" in r.text and "Mensagem do fluxo" in r.text
    assert "code 10" in r.text and "linha-erro" in r.text
    so_erros = c.get("/logs?grupo=erros").text
    assert "code 10" in so_erros and "Webhook recebido" not in so_erros
    busca = c.get("/logs?busca=fulana").text
    assert "@fulana" in busca and "Webhook recebido" not in busca


def test_menu_tem_logs_abaixo_de_leads(monkeypatch):
    c = _cliente_logado(monkeypatch)
    html = c.get("/logs").text
    assert html.index('href="/leads"') < html.index('href="/logs"')
