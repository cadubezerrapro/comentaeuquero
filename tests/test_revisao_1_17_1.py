"""Revisão 1.17.1: horário local nas telas e nenhum segredo em log de erro."""
import requests

from app import db, instagram, main, runtime


def test_horario_local_nas_telas(monkeypatch):
    monkeypatch.setattr(main, "FUSO_HORAS", -3)
    assert main._local("2026-11-06T12:36:00Z") == "06/11 09:36"
    assert main._local("2026-11-06T01:10:00Z") == "05/11 22:10"     # vira o dia
    assert main._local("") == "" and main._local(None) == ""
    assert main.templates.env.filters["dia_local"]("2026-11-06T01:10:00Z") == "05/11"


def test_entregas_por_dia_no_fuso_do_painel(monkeypatch):
    monkeypatch.delenv("CEQ_FUSO_HORAS", raising=False)
    db.conn().execute("DELETE FROM events"); db.conn().commit()
    db.conn().execute("INSERT INTO events (ts, kind, ok) VALUES ('2026-11-06T01:30:00Z', 'fluxo_envio', 1)")
    db.conn().commit()
    dias = [d for d, _ in db.stats()["per_day"]]
    assert dias == ["2026-11-05"]          # 22h30 de Brasília ainda é dia 5


def test_limpador_pega_token_e_chave_em_qualquer_url():
    for cru in ("x?access_token=EAAB1", "https://h.com/a?api_key=k1&ok=1", "?token=t1",
                "?client_secret=s1", "?signature=abc", "?senha=123"):
        assert "***" in instagram.sem_segredo(cru)
    assert instagram.sem_segredo("palavra key no texto") == "palavra key no texto"


def test_erro_de_rede_no_worker_nao_grava_o_token(monkeypatch):
    def explode():
        requests.get("http://127.0.0.1:9/v21.0/me", params={"access_token": "TOKEN_QUE_VAZARIA"},
                     timeout=2)
    monkeypatch.setattr(runtime, "tick", explode)
    monkeypatch.setattr(runtime.time, "sleep", lambda s: (_ for _ in ()).throw(SystemExit))
    try:
        runtime.worker_loop()
    except SystemExit:
        pass
    ultimo = db.conn().execute(
        "SELECT payload FROM events WHERE kind='worker_erro' ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert "TOKEN_QUE_VAZARIA" not in ultimo and "access_token=***" in ultimo
