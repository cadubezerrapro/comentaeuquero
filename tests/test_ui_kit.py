"""Modais e dropdowns próprios (1.14.0): nada de janela nativa do navegador."""
import pathlib
import re

import pytest
from fastapi.testclient import TestClient

from app import main

RAIZ = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def client_logado(monkeypatch):
    monkeypatch.setattr(main, "logged_in", lambda request: True)
    monkeypatch.setattr(main, "require_login", lambda request: None)
    return TestClient(main.app)


def test_nenhum_template_usa_janela_nativa():
    for p in (RAIZ / "app" / "templates").glob("*.html"):
        txt = p.read_text(encoding="utf-8")
        assert not re.search(r"(?<![\w.])(confirm|prompt|alert)\(", txt), p.name


def test_editor_nao_usa_janela_nativa():
    for p in (RAIZ / "editor" / "src").glob("*.vue"):
        txt = p.read_text(encoding="utf-8")
        assert not re.search(r"(?<![\w.])(confirm|prompt|alert)\(", txt), p.name


def test_painel_carrega_o_kit_com_versao(client_logado):
    r = client_logado.get("/painel")
    assert r.status_code == 200
    assert re.search(r'/static/ceq-ui\.js\?v=[0-9a-f]{10}', r.text)
    assert client_logado.get("/static/ceq-ui.js").status_code == 200


def test_editor_carrega_o_kit_com_versao(client_logado):
    r = client_logado.get("/editor")
    assert r.status_code == 200
    assert re.search(r'/static/ceq-ui\.js\?v=[0-9a-f]{10}', r.text)


def test_formularios_destrutivos_pedem_confirmacao():
    # o confirm do navegador virou data-confirmar: se alguém voltar pro onsubmit
    # com confirm(), o primeiro teste acima pega; aqui garante que os perigosos
    # continuam marcados como tal
    leads = (RAIZ / "app" / "templates" / "leads.html").read_text(encoding="utf-8")
    assert "data-confirmar-perigo" in leads
