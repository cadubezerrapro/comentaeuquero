"""Lead é só quem entrou num funil (1.16.0).

Direct comum, leitura de mensagem e comentário com o fluxo desligado não viram lead e
não consultam o perfil na Meta. Quem dispara um fluxo ligado vira lead com a data de
entrada e a palavra que usou."""
import uuid

import pytest

from app import db, flowengine, instagram, runtime


@pytest.fixture
def conta(monkeypatch):
    monkeypatch.setattr(runtime, "THROTTLE_S", 0)
    monkeypatch.setattr(runtime, "LIMITER", runtime.RateLimiter(1000))
    db.set_ajuste("throttle_until", "")
    acc = db.upsert_account(uuid.uuid4().hex, "", "conta_ig", "tok", "2099-01-01T00:00:00Z")
    db.conn().execute("DELETE FROM accounts WHERE id<>?", (acc["id"],)); db.conn().commit()
    perfis = []
    monkeypatch.setattr(instagram, "fetch_profile", lambda c, igsid: perfis.append(igsid) or
                        {"username": f"u{igsid}", "is_user_follow_business": True})
    for nome in ("send_text", "send_buttons", "send_quick_replies"):
        monkeypatch.setattr(instagram, nome, lambda *a, **k: (True, "", {}))
    monkeypatch.setattr(instagram, "send_private_reply", lambda *a, **k: (True, "", {}),
                        raising=False)
    monkeypatch.setattr(instagram, "send_public_reply", lambda *a, **k: (True, "", {}))
    return db.get_account(acc["id"]), perfis


def _fluxo(acc, ativo=True, kws=("viral", "quero viral")):
    f = db.create_flow(acc["id"], name="Isca VIRAL", entry_node="n0", graph={
        "nodes": [{"id": "n0", "type": "text", "data": {"text": "toma"}}], "edges": []})
    db.update_flow(f, active=1 if ativo else 0)
    for tipo in ("comment", "dm"):
        db.add_trigger(f, tipo, list(kws))
    return f


def _dm(acc, igsid, texto):
    flowengine.process_payload({"object": "instagram", "entry": [{"id": acc["ig_id"], "messaging": [
        {"sender": {"id": igsid}, "message": {"mid": uuid.uuid4().hex, "text": texto}}]}]})


def _lido(acc, igsid):
    flowengine.process_payload({"object": "instagram", "entry": [{"id": acc["ig_id"], "messaging": [
        {"sender": {"id": igsid}, "read": {"mid": "x"}}]}]})


def _comentario(acc, igsid, texto):
    flowengine.process_payload({"object": "instagram", "entry": [{"id": acc["ig_id"], "changes": [
        {"field": "comments", "value": {"id": uuid.uuid4().hex, "text": texto,
                                        "from": {"id": igsid, "username": f"u{igsid}"},
                                        "media": {"id": "m1"}}}]}]})


def _linhas():
    return db.conn().execute("SELECT COUNT(*) FROM leads").fetchone()[0]


def test_direct_comum_nao_vira_lead_nem_consulta_perfil(conta):
    acc, perfis = conta
    _fluxo(acc)
    _dm(acc, "100", "oi, tudo bem? vi seu vídeo")
    _lido(acc, "100")
    assert _linhas() == 0 and perfis == []
    assert db.leads_resumo(acc["id"])["total"] == 0


def test_palavra_com_fluxo_desligado_nao_vira_lead_e_avisa_no_log(conta):
    acc, perfis = conta
    _fluxo(acc, ativo=False)
    _comentario(acc, "200", "viral")
    _dm(acc, "201", "quero viral")
    assert _linhas() == 0 and perfis == []
    avisos = db.conn().execute("SELECT who FROM events WHERE kind='fluxo_desligado'").fetchall()
    assert sorted(a[0] for a in avisos) == ["201", "u200"]


def test_comentario_no_fluxo_ligado_vira_lead_com_palavra_e_data(conta):
    acc, perfis = conta
    _fluxo(acc)
    _comentario(acc, "300", "EU QUERO VIRAL!!")
    lead = db.lead_por_igsid(acc["id"], "300")
    assert lead["entrou_funil_em"] and lead["last_keyword"] == "viral"
    assert perfis == ["300"]
    assert [l["igsid"] for l in db.list_leads(acc["id"])] == ["300"]


def test_dm_com_palavra_grava_a_palavra(conta):
    acc, _ = conta
    _fluxo(acc, kws=("quero viral", "viral"))
    _dm(acc, "400", "quero viral")
    assert db.lead_por_igsid(acc["id"], "400")["last_keyword"] == "quero viral"


def test_lead_do_funil_que_manda_direct_depois_continua_lead(conta):
    acc, perfis = conta
    _fluxo(acc)
    _comentario(acc, "500", "viral")
    antes = db.lead_por_igsid(acc["id"], "500")
    _dm(acc, "500", "valeu demais")
    _lido(acc, "500")
    depois = db.lead_por_igsid(acc["id"], "500")
    assert depois["interactions"] == antes["interactions"] + 1
    assert depois["entrou_funil_em"] == antes["entrou_funil_em"]
    assert perfis == ["500"]                     # perfil consultado uma vez só
    lidos = db.conn().execute("SELECT COUNT(*) FROM events WHERE kind='fluxo_lido'").fetchone()[0]
    assert lidos == 1


def test_botao_de_mensagem_antiga_sem_lead_nao_cria(conta):
    acc, _ = conta
    flowengine.process_payload({"object": "instagram", "entry": [{"id": acc["ig_id"], "messaging": [
        {"sender": {"id": "600"}, "postback": {"mid": "pb1", "payload": "manda"}}]}]})
    assert _linhas() == 0
    ev = db.conn().execute("SELECT payload FROM events WHERE kind='fluxo_postback'").fetchone()
    assert "sem_lead" in ev[0]


def test_contato_antigo_some_da_lista_e_quem_teve_sessao_vira_lead(conta):
    acc, _ = conta
    f = _fluxo(acc)
    comum = db.touch_lead(acc["id"], "700", "", "so.mandou.direct")
    passou = db.touch_lead(acc["id"], "701", "viral", "passou.no.fluxo")
    db.open_session(acc["id"], passou["id"], f, node_id="n0")
    db.conn().execute("UPDATE leads SET entrou_funil_em=''"); db.conn().commit()
    db.init()                                    # migração roda de novo, idempotente
    assert db.lead_por_igsid(acc["id"], "701")["entrou_funil_em"]
    assert not db.lead_por_igsid(acc["id"], "700")["entrou_funil_em"]
    assert [l["username"] for l in db.list_leads(acc["id"])] == ["passou.no.fluxo"]
    assert db.leads_count(acc["id"]) == 1 and comum   # não apagou ninguém, só não lista
