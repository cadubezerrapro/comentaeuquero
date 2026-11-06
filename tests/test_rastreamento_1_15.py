"""Link rastreado e reconsulta de seguidores (1.15.0)."""
import uuid

import pytest

from app import db, instagram, links, runtime, seguidores

DESTINO = "https://ia-thefuture.vercel.app/#item-tut-clonar-viral"


@pytest.fixture(autouse=True)
def _sem_throttle(monkeypatch):
    monkeypatch.setattr(runtime, "THROTTLE_S", 0)
    monkeypatch.setattr(runtime, "LIMITER", runtime.RateLimiter(1000))
    db.set_ajuste("throttle_until", "")
    db.set_ajuste(seguidores.AJUSTE_PAUSA, "")
    db.set_ajuste(seguidores.AJUSTE_ULTIMA, "")


@pytest.fixture
def ig(monkeypatch):
    enviados = []

    def _ok(nome):
        def f(account, recipient, texto, *a, **k):
            enviados.append((nome, texto, a))
            return True, "", {}
        return f
    monkeypatch.setattr(instagram, "send_text", _ok("texto"))
    monkeypatch.setattr(instagram, "send_buttons", _ok("botoes"))
    monkeypatch.setattr(instagram, "send_quick_replies", _ok("quick"))
    monkeypatch.setattr(instagram, "fetch_profile", lambda *a, **k: {})
    acc = db.upsert_account(uuid.uuid4().hex, "", "conta_ig", "tok-ig", "2099-01-01T00:00:00Z")
    db.conn().execute("DELETE FROM accounts WHERE id<>?", (acc["id"],)); db.conn().commit()
    return db.get_account(acc["id"]), enviados


def _roda(acc, grafo, igsid="111", username="maria"):
    f = db.create_flow(acc["id"], name="Isca VIRAL", graph=grafo, entry_node="n0")
    lead = db.touch_lead(acc["id"], igsid, "", username)
    db.abrir_janela(lead["id"], "ig")
    runtime.start(acc, db.get_flow(f), lead)
    return db.get_lead(lead["id"])


def _grafo_texto(texto="Tá aqui: {link}", link=DESTINO):
    return {"nodes": [{"id": "n0", "type": "text", "data": {"text": texto, "link": link}}],
            "edges": []}


def _token_de(texto):
    return texto.split("ceq=")[1].split("#")[0].split()[0]


# ---------- link: modo parâmetro (padrão) ----------

def test_parametro_mantem_dominio_real_e_ancora(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    monkeypatch.delenv("CEQ_LINK_RASTREADO", raising=False)
    _roda(acc, _grafo_texto())
    texto = env[-1][1]
    assert "https://ia-thefuture.vercel.app/?ceq=" in texto
    assert texto.endswith("#item-tut-clonar-viral")
    assert "railway" not in texto and "/r/" not in texto
    assert texto.count("http") == 1


def test_sem_dominio_configurado_link_sai_intocado(ig, monkeypatch):
    acc, env = ig
    monkeypatch.delenv("CEQ_LINK_DOMINIOS", raising=False)
    _roda(acc, _grafo_texto())
    assert env[-1][1] == f"Tá aqui: {DESTINO}"


def test_dominio_de_terceiro_nao_recebe_parametro(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    _roda(acc, _grafo_texto(link="https://youtube.com/watch?v=abc"))
    assert "ceq=" not in env[-1][1]


def test_link_anexado_no_fim_e_link_escrito_no_texto(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    _roda(acc, _grafo_texto(texto="Tá aqui o passo a passo"), "1")
    assert "?ceq=" in env[-1][1] and env[-1][1].startswith("Tá aqui o passo a passo\n")
    _roda(acc, _grafo_texto(texto=f"Abre: {DESTINO} valeu"), "2", "joao")
    assert env[-1][1].count("ceq=") == 1 and "valeu" in env[-1][1]


def test_mesmo_lead_mesmo_no_reaproveita_token(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    lead = _roda(acc, _grafo_texto())
    t1 = _token_de(env[-1][1])
    assert db.token_link(acc["id"], lead["id"], "Isca VIRAL", "n0", DESTINO) == t1
    outro = db.touch_lead(acc["id"], "999", "", "outra")
    assert db.token_link(acc["id"], outro["id"], "Isca VIRAL", "n0", DESTINO) != t1


def test_botao_de_link_rastreado(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    vistos = []
    monkeypatch.setattr(instagram, "send_buttons",
                        lambda a, r, t, botoes: vistos.append(botoes) or (True, "", {}))
    grafo = {"nodes": [{"id": "n0", "type": "buttons", "data": {
        "text": "Toca", "buttons": [{"title": "Abrir", "type": "url", "url": DESTINO}]}}],
        "edges": []}
    _roda(acc, grafo)
    assert "?ceq=" in vistos[-1][0]["url"]


def test_visto_conta_clique_uma_vez_e_entra_no_funil(client, ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    _roda(acc, _grafo_texto())
    token = _token_de(env[-1][1])
    h = {"Origin": "https://ia-thefuture.vercel.app",
         "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0) Safari/604.1"}
    r = client.post(f"/r/{token}/visto", headers=h)
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == "https://ia-thefuture.vercel.app"
    client.post(f"/r/{token}/visto", headers=h)            # recarregou a página
    link = db.link_por_token(token)
    assert link["cliques"] == 2 and link["primeiro_clique_em"]
    eventos = db.conn().execute(
        "SELECT * FROM events WHERE kind='link_clique' AND who='maria'").fetchall()
    assert len(eventos) == 1
    assert db.funil(acc["id"], flow_name="Isca VIRAL")[0]["clicaram"] == 1


def test_visto_recusa_origem_desconhecida_e_robo(client, ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    _roda(acc, _grafo_texto())
    token = _token_de(env[-1][1])
    assert client.post(f"/r/{token}/visto",
                       headers={"Origin": "https://golpe.example"}).status_code == 403
    assert client.post(f"/r/{token}/visto").status_code == 403          # sem Origin
    client.post(f"/r/{token}/visto", headers={"Origin": "https://ia-thefuture.vercel.app",
                                              "User-Agent": "facebookexternalhit/1.1"})
    assert db.link_por_token(token)["cliques"] == 0


def test_visto_token_inexistente_nao_vira_oraculo(client, monkeypatch):
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    r = client.post("/r/naoexiste1234/visto",
                    headers={"Origin": "https://ia-thefuture.vercel.app", "User-Agent": "Mozilla"})
    assert r.status_code == 204


# ---------- link: modo redirecionar (opcional) ----------

def test_redirecionar_mesmo_destino_pra_robo_e_pessoa(client, ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_RASTREADO", "redirecionar")
    monkeypatch.setenv("BASE_URL", "https://ceq.exemplo.com")
    _roda(acc, _grafo_texto())
    texto = env[-1][1]
    assert "https://ceq.exemplo.com/r/" in texto
    token = texto.split("/r/")[1].split()[0]
    robo = client.get(f"/r/{token}", headers={"User-Agent": "facebookexternalhit/1.1"},
                      follow_redirects=False)
    gente = client.get(f"/r/{token}", headers={"User-Agent": "Mozilla/5.0 Instagram"},
                       follow_redirects=False)
    assert robo.status_code == gente.status_code == 302
    assert robo.headers["location"] == gente.headers["location"] == DESTINO   # sem cloaking
    assert db.link_por_token(token)["cliques"] == 1                        # só a pessoa


def test_redirecionar_token_desconhecido_e_404_nunca_redireciona(client):
    assert client.get("/r/abcdefghijkl", follow_redirects=False).status_code == 404
    assert client.get("/r/%2F%2Fgolpe.com", follow_redirects=False).status_code == 404


def test_redirecionar_sem_base_https_nao_troca(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_RASTREADO", "redirecionar")
    monkeypatch.setenv("BASE_URL", "")
    _roda(acc, _grafo_texto())
    assert env[-1][1] == f"Tá aqui: {DESTINO}"


def test_desligado_nao_mexe(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_RASTREADO", "desligado")
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    _roda(acc, _grafo_texto())
    assert env[-1][1] == f"Tá aqui: {DESTINO}"


def test_com_parametro_preserva_query():
    assert links.com_parametro("https://a.com/p?x=1&ceq=velho#h", "TOK12345") == \
        "https://a.com/p?x=1&ceq=TOK12345#h"


# ---------- reconsulta de seguidores ----------

@pytest.fixture
def conta(monkeypatch):
    acc = db.upsert_account(uuid.uuid4().hex, "", "conta_ig", "tok-ig", "2099-01-01T00:00:00Z")
    db.conn().execute("DELETE FROM accounts WHERE id<>?", (acc["id"],)); db.conn().commit()
    monkeypatch.setattr(seguidores, "TAGS", ["isca_viral"])
    return db.get_account(acc["id"])


def _lead(conta, igsid, segue=1, tag="isca_viral"):
    l = db.touch_lead(conta["id"], igsid, "", f"u{igsid}")
    db.marca_funil(l["id"])
    db.conn().execute("UPDATE leads SET is_follower=? WHERE id=?", (segue, l["id"]))
    db.conn().commit()
    if tag:
        db.add_tag(l["id"], tag)
    return l


def _meta(monkeypatch, respostas):
    chamadas = []

    def f(conta, igsid):
        chamadas.append(igsid)
        r = respostas.get(igsid, ("segue", 0.0, ""))
        return r
    monkeypatch.setattr(instagram, "consulta_seguidor", f)
    return chamadas


def test_deixou_de_seguir_grava_data_e_etiqueta(conta, monkeypatch):
    a = _lead(conta, "1")
    b = _lead(conta, "2")
    _meta(monkeypatch, {"1": ("nao_segue", 5.0, ""), "2": ("segue", 5.0, "")})
    r = seguidores.rodar(conta, intervalo=0)
    assert r["deixaram"] == 1 and r["conferidos"] == 2 and not r["parou"]
    la = db.get_lead(a["id"])
    assert la["is_follower"] == 0 and la["deixou_de_seguir_em"]
    assert db.has_tag(a["id"], "deixou_de_seguir")
    assert db.get_lead(b["id"])["is_follower"] == 1


def test_voltou_a_seguir_tira_etiqueta(conta, monkeypatch):
    a = _lead(conta, "1")
    _meta(monkeypatch, {"1": ("nao_segue", 0.0, "")})
    seguidores.rodar(conta, intervalo=0)
    _meta(monkeypatch, {"1": ("segue", 0.0, "")})
    r = seguidores.rodar(conta, intervalo=0)
    assert r["voltaram"] == 1 and not db.has_tag(a["id"], "deixou_de_seguir")


def test_meta_nao_informou_vira_desconhecido_nunca_segue(conta, monkeypatch):
    a = _lead(conta, "1")
    _meta(monkeypatch, {"1": ("desconhecido", 0.0, "campo ausente")})
    seguidores.rodar(conta, intervalo=0)
    assert db.get_lead(a["id"])["is_follower"] is None


def test_erro_de_rede_nao_apaga_status(conta, monkeypatch):
    a = _lead(conta, "1")
    _meta(monkeypatch, {"1": ("erro", 0.0, "timeout")})
    r = seguidores.rodar(conta, intervalo=0)
    assert r["erros"] == 1 and db.get_lead(a["id"])["is_follower"] == 1
    assert not db.get_lead(a["id"])["seguidor_checado_em"]   # volta na próxima rodada


def test_freio_da_meta_para_tudo_e_trava_envio(conta, monkeypatch):
    _lead(conta, "1"); _lead(conta, "2")
    chamadas = _meta(monkeypatch, {"1": ("freio", 0.0, "code 4"), "2": ("segue", 0.0, "")})
    r = seguidores.rodar(conta, intervalo=0)
    assert r["parou"] == "freio_meta" and len(chamadas) == 1
    assert instagram.cooldown_restante() > 0          # o motor de envio respeita também
    r2 = seguidores.rodar(conta, intervalo=0)
    assert r2["parou"] in ("freio_meta", "pausada") and len(chamadas) == 1


def test_uso_alto_para_a_rodada(conta, monkeypatch):
    _lead(conta, "1"); _lead(conta, "2")
    chamadas = _meta(monkeypatch, {"1": ("segue", 75.0, ""), "2": ("segue", 0.0, "")})
    r = seguidores.rodar(conta, intervalo=0)
    assert r["parou"].startswith("uso_meta") and len(chamadas) == 1


def test_token_ruim_para_sem_mexer_em_ninguem(conta, monkeypatch):
    a = _lead(conta, "1"); _lead(conta, "2")
    chamadas = _meta(monkeypatch, {"1": ("parar", 0.0, "code 190")})
    r = seguidores.rodar(conta, intervalo=0)
    assert r["parou"] == "token_ou_permissao" and len(chamadas) == 1
    assert db.get_lead(a["id"])["is_follower"] == 1


def test_so_quem_tem_etiqueta_e_consta_como_seguidor(conta, monkeypatch):
    _lead(conta, "1")                       # entra
    _lead(conta, "2", tag="")               # sem a etiqueta
    _lead(conta, "3", segue=0)              # já não segue (e nunca deixou)
    _lead(conta, "4", segue=None)           # desconhecido
    chamadas = _meta(monkeypatch, {})
    seguidores.rodar(conta, intervalo=0)
    assert chamadas == ["1"]


def test_respeita_limite_e_espaca_as_consultas(conta, monkeypatch):
    for i in range(5):
        _lead(conta, str(i))
    chamadas = _meta(monkeypatch, {})
    sonos = []
    seguidores.rodar(conta, limite=3, intervalo=7, dormir=sonos.append)
    assert len(chamadas) == 3 and sonos == [7, 7]


def test_nao_roda_durante_freio_do_envio(conta, monkeypatch):
    _lead(conta, "1")
    chamadas = _meta(monkeypatch, {})
    db.set_ajuste("throttle_until", db.in_seconds_iso(600))
    assert seguidores.rodar(conta, intervalo=0)["parou"] == "freio_meta" and not chamadas


def test_vencida_respeita_periodo(monkeypatch):
    monkeypatch.setattr(seguidores, "HORAS", 24)
    db.set_ajuste(seguidores.AJUSTE_ULTIMA, "")
    assert seguidores.vencida()
    db.set_ajuste(seguidores.AJUSTE_ULTIMA, db.now_iso())
    assert not seguidores.vencida()
    monkeypatch.setattr(seguidores, "HORAS", 0)
    db.set_ajuste(seguidores.AJUSTE_ULTIMA, "")
    assert not seguidores.vencida()


# ---------- consulta_seguidor: separa os casos ----------

class _R:
    def __init__(self, status, body, headers=None):
        self.status_code, self._b, self.headers = status, body, headers or {}

    def json(self):
        return self._b


@pytest.mark.parametrize("status,body,esperado", [
    (200, {"is_user_follow_business": True}, "segue"),
    (200, {"is_user_follow_business": False}, "nao_segue"),
    (200, {"id": "1"}, "desconhecido"),
    (400, {"error": {"code": 100, "message": "consent"}}, "desconhecido"),
    (400, {"error": {"code": 4}}, "freio"),
    (400, {"error": {"code": 190}}, "parar"),
    (500, {"error": {"code": 1}}, "erro"),
])
def test_consulta_seguidor_casos(monkeypatch, status, body, esperado):
    monkeypatch.setattr(instagram.requests, "get", lambda *a, **k: _R(status, body))
    assert instagram.consulta_seguidor({"id": 1, "access_token": "t"}, "9")[0] == esperado


def test_consulta_seguidor_le_uso(monkeypatch):
    h = {"X-Business-Use-Case-Usage":
         '{"123": [{"type": "instagram", "call_count": 72, "total_time": 10}]}'}
    monkeypatch.setattr(instagram.requests, "get",
                        lambda *a, **k: _R(200, {"is_user_follow_business": True}, h))
    assert instagram.consulta_seguidor({"id": 1, "access_token": "t"}, "9")[1] == 72


def test_consulta_seguidor_rede(monkeypatch):
    def boom(*a, **k):
        raise instagram.requests.ConnectionError("x")
    monkeypatch.setattr(instagram.requests, "get", boom)
    assert instagram.consulta_seguidor({"id": 1, "access_token": "t"}, "9")[0] == "erro"


def test_troca_links_nao_estraga_nem_deixa_copia_crua():
    o, n = "https://a.com/x", "https://a.com/x?ceq=TOK12345"
    assert runtime._troca_links(f"{n}\n{o}", [(o, n)]) == f"{n}\n{n}"
    assert runtime._troca_links(f"veja {o} ok", [(o, n)]) == f"veja {n} ok"
    assert runtime._troca_links(n, [(o, n)]) == n


def test_primeira_resposta_de_comentario_texto_com_botoes_rastreia(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setenv("CEQ_LINK_DOMINIOS", "ia-thefuture.vercel.app")
    grafo = {"nodes": [
        {"id": "n0", "type": "text", "data": {"text": "Tá aqui", "link": DESTINO}},
        {"id": "n1", "type": "buttons", "data": {"text": "Quer mais?",
                                                 "buttons": [{"title": "Sim", "key": "s"}]}}],
        "edges": [{"id": "a", "source": "n0", "target": "n1"}]}
    f = db.create_flow(acc["id"], name="Isca VIRAL", graph=grafo, entry_node="n0")
    lead = db.touch_lead(acc["id"], "321", "", "bia")
    runtime.start(acc, db.get_flow(f), lead, comment_id="c1")
    botoes = [e for e in env if e[0] == "botoes"][-1][1]
    assert "?ceq=" in botoes and botoes.count("ia-thefuture") == 1
    assert db.conn().execute("SELECT node_id FROM links_rastreados WHERE lead_id=?",
                             (lead["id"],)).fetchone()[0] == "n0"


# ---------- portão de seguidor: pedido, não muro ----------

def _grafo_portao(libera_apos=None):
    cond = {"check": "e_seguidor"}
    if libera_apos is not None:
        cond["libera_apos"] = libera_apos
    return {"nodes": [
        {"id": "n0", "type": "condition", "data": cond},
        {"id": "pede", "type": "buttons", "data": {"text": "Segue e toca",
                                                   "buttons": [{"title": "Já segui", "key": "segui"}]}},
        {"id": "entrega", "type": "text", "data": {"text": "conteudo entregue"}}],
        "edges": [{"id": "a", "source": "n0", "target": "entrega", "sourceHandle": "sim"},
                  {"id": "b", "source": "n0", "target": "pede", "sourceHandle": "nao"},
                  {"id": "c", "source": "pede", "target": "n0", "sourceHandle": "segui"}]}


def _nao_segue(monkeypatch):
    monkeypatch.setattr(instagram, "fetch_profile",
                        lambda *a, **k: {"username": "x", "is_user_follow_business": False})


def test_portao_pede_uma_vez_e_depois_entrega(ig, monkeypatch):
    acc, env = ig
    _nao_segue(monkeypatch)
    lead = _roda(acc, _grafo_portao())
    assert [e[0] for e in env] == ["botoes"]                  # pediu
    runtime.resume_postback(acc, db.get_lead(lead["id"]), "segui")
    assert env[-1][1] == "conteudo entregue"                  # entregou mesmo sem follow
    assert db.conn().execute("SELECT COUNT(*) FROM events WHERE kind='seguidor_liberado'"
                             ).fetchone()[0] >= 1


def test_portao_zero_e_muro_explicito(ig, monkeypatch):
    acc, env = ig
    _nao_segue(monkeypatch)
    lead = _roda(acc, _grafo_portao(libera_apos=0))
    runtime.resume_postback(acc, db.get_lead(lead["id"]), "segui")
    assert all(e[1] != "conteudo entregue" for e in env)


def test_portao_quem_segue_nem_ve_o_pedido(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setattr(instagram, "fetch_profile",
                        lambda *a, **k: {"username": "x", "is_user_follow_business": True})
    _roda(acc, _grafo_portao())
    assert [e[1] for e in env] == ["conteudo entregue"]


# ---------- enrich_lead: campo ausente não vira "não segue" ----------

def test_enrich_sem_campo_fica_desconhecido(ig):
    acc, _ = ig
    db.touch_lead(acc["id"], "555", "", "z")
    db.enrich_lead(acc["id"], "555", {"username": "z"})
    assert db.conn().execute("SELECT is_follower FROM leads WHERE igsid='555'").fetchone()[0] is None
    db.enrich_lead(acc["id"], "555", {"username": "z", "is_user_follow_business": False})
    assert db.conn().execute("SELECT is_follower FROM leads WHERE igsid='555'").fetchone()[0] == 0


def test_perfil_sem_campo_nao_prende_no_pedido(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setattr(instagram, "fetch_profile", lambda *a, **k: {"username": "x"})
    _roda(acc, _grafo_portao(libera_apos=0))
    assert [e[1] for e in env] == ["conteudo entregue"]


# ---------- balde de mensagens com link ----------

def test_balde_de_links_adia_sem_perder(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setattr(runtime, "LIMITER_LINKS", runtime.RateLimiter(1))
    _roda(acc, _grafo_texto(), "1", "a")
    _roda(acc, _grafo_texto(), "2", "b")
    _roda(acc, _grafo_texto(texto="sem link nenhum", link=""), "3", "c")
    textos = [e[1] for e in env]
    assert sum("http" in t for t in textos) == 1             # só 1 link por vez
    assert "sem link nenhum" in textos                        # mensagem sem link passa
    adiado = db.conn().execute(
        "SELECT payload FROM events WHERE kind='envio_adiado' ORDER BY id DESC LIMIT 1").fetchone()
    assert "sem ficha link" in adiado[0]
    job = db.conn().execute("SELECT run_at FROM jobs WHERE status='pendente' "
                            "ORDER BY id DESC LIMIT 1").fetchone()
    assert job and job[0] > db.in_seconds_iso(600)            # espera a vez, não martela


def test_balde_de_links_desligado(ig, monkeypatch):
    acc, env = ig
    monkeypatch.setattr(runtime, "LIMITER_LINKS", None)
    for i in range(3):
        _roda(acc, _grafo_texto(), str(10 + i), f"p{i}")
    assert sum("http" in e[1] for e in env) == 3
