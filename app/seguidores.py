"""Reconsulta de seguidores (1.15.0): quem parou de seguir a conta.

A API do Instagram não avisa unfollow. O status de seguidor só era conferido quando a
pessoa passava por um nó Condição. Aqui uma tarefa de fundo reconfere, uma vez por
período, os leads que constavam como seguidores e grava quando algum deixou de seguir
(campo leads.deixou_de_seguir_em + etiqueta `deixou_de_seguir`).

Cuidado com a conta é o desenho, não um detalhe:

- Só lê (GET do perfil). Nunca manda mensagem pra quem deixou de seguir: cobrar
  unfollow por DM é o tipo de automação que vira denúncia e spam.
- Só consulta quem já conversou com a conta (é o que a Meta exige pra devolver o
  perfil) e, por padrão, só quem tem a etiqueta configurada (isca_viral).
- Devagar: um perfil a cada CEQ_RECONSULTA_INTERVALO_S segundos, no máximo
  CEQ_RECONSULTA_MAX por rodada.
- Para ao primeiro sinal da Meta: código de throttle (e respeita o freio global que
  o motor de envio já usa), uso acima de USO_LIMITE % nos headers de rate limit, ou
  token inválido. Envio de mensagem tem prioridade sobre esta tarefa, sempre.
- Erro de rede não apaga status de ninguém: o lead fica pra próxima rodada.
- "A Meta não informou" vira desconhecido (NULL), nunca "segue".
"""
import os
import threading
import time

from . import db, instagram


def _int_env(nome, padrao):
    try:
        return int(os.environ.get(nome, "") or padrao)
    except ValueError:
        return padrao


HORAS = _int_env("CEQ_RECONSULTA_HORAS", 24)            # 0 desliga
MAX_POR_RODADA = _int_env("CEQ_RECONSULTA_MAX", 150)
INTERVALO_S = _int_env("CEQ_RECONSULTA_INTERVALO_S", 3)
# vazio = qualquer lead que conste como seguidor; "*" idem
TAGS = [t.strip() for t in os.environ.get("CEQ_RECONSULTA_TAGS", "isca_viral").split(",")
        if t.strip() and t.strip() != "*"]
USO_LIMITE = 60.0            # % do limite da Meta: acima disso a rodada para
PAUSA_APOS_FREIO_S = 6 * 3600
ERROS_SEGUIDOS_MAX = 3

AJUSTE_ULTIMA = "reconsulta_ultima"
AJUSTE_PAUSA = "reconsulta_pausa_ate"

_RODANDO = threading.Lock()


def _pausada() -> bool:
    ate = db.get_ajuste(AJUSTE_PAUSA)
    return bool(ate) and ate > db.now_iso()


def vencida() -> bool:
    """Já passou o período desde a última rodada?"""
    if HORAS <= 0:
        return False
    ultima = db.get_ajuste(AJUSTE_ULTIMA)
    return not ultima or ultima <= db.in_seconds_iso(-HORAS * 3600)


def rodar(conta, limite=None, intervalo=None, dormir=time.sleep) -> dict:
    """Uma rodada pra uma conta. Síncrona e testável (dormir é injetável).

    Devolve o resumo: conferidos, deixaram, voltaram, desconhecidos, erros, parou."""
    resumo = {"conferidos": 0, "deixaram": 0, "voltaram": 0, "desconhecidos": 0,
              "erros": 0, "parou": ""}
    if not _RODANDO.acquire(blocking=False):
        resumo["parou"] = "ja_rodando"
        return resumo
    try:
        if instagram.cooldown_restante() > 0:
            resumo["parou"] = "freio_meta"
            return resumo
        if _pausada():
            resumo["parou"] = "pausada"
            return resumo
        if instagram.token_invalido(conta):
            resumo["parou"] = "token_invalido"
            return resumo
        espera = INTERVALO_S if intervalo is None else intervalo
        leads = db.leads_para_reconsultar(conta["id"], TAGS,
                                          MAX_POR_RODADA if limite is None else limite)
        erros_seguidos = 0
        for i, lead in enumerate(leads):
            if i:
                dormir(espera)
            # o motor de envio pode ter levado freio no meio da rodada
            if instagram.cooldown_restante() > 0:
                resumo["parou"] = "freio_meta"
                break
            status, uso, detalhe = instagram.consulta_seguidor(conta, lead["igsid"])
            if status == "freio":
                instagram._entra_em_cooldown(instagram.COOLDOWN_PADRAO_S, "reconsulta_seguidores")
                db.set_ajuste(AJUSTE_PAUSA, db.in_seconds_iso(PAUSA_APOS_FREIO_S))
                resumo["parou"] = "freio_meta"
                db.log_event("reconsulta_freio", conta["id"], ok=False,
                             payload={"detalhe": detalhe})
                break
            if status == "parar":
                resumo["parou"] = "token_ou_permissao"
                db.log_event("reconsulta_erro", conta["id"], ok=False,
                             payload={"detalhe": detalhe})
                break
            if status == "erro":
                resumo["erros"] += 1
                erros_seguidos += 1
                if erros_seguidos >= ERROS_SEGUIDOS_MAX:
                    resumo["parou"] = "erros_seguidos"
                    db.log_event("reconsulta_erro", conta["id"], ok=False,
                                 payload={"detalhe": detalhe})
                    break
                continue
            erros_seguidos = 0
            resumo["conferidos"] += 1
            mudanca = db.gravar_seguidor(lead["id"], status)
            who = lead.get("username") or ""
            if mudanca == "deixou":
                resumo["deixaram"] += 1
                db.log_event("deixou_de_seguir", conta["id"], "", "reconsulta", True, who)
            elif mudanca == "voltou":
                resumo["voltaram"] += 1
                db.log_event("voltou_a_seguir", conta["id"], "", "reconsulta", True, who)
            elif status == "desconhecido":
                resumo["desconhecidos"] += 1
            if uso >= USO_LIMITE:
                db.set_ajuste(AJUSTE_PAUSA, db.in_seconds_iso(PAUSA_APOS_FREIO_S))
                resumo["parou"] = f"uso_meta_{int(uso)}%"
                break
        db.set_ajuste(AJUSTE_ULTIMA, db.now_iso())
        db.log_event("reconsulta_seguidores", conta["id"],
                     ok=not resumo["parou"] or resumo["parou"].startswith("uso_meta"),
                     payload=resumo)
        return resumo
    finally:
        _RODANDO.release()


def rodar_todas() -> list:
    return [rodar(conta) for conta in db.all_accounts()]


def loop(checar_a_cada_s=600):
    """Thread de fundo. Separada do worker do motor de propósito: uma rodada leva
    minutos (o intervalo entre consultas é proposital) e o worker não pode atrasar
    delay de fluxo por causa disso."""
    time.sleep(120)   # deixa a subida (webhooks, fotos) passar primeiro
    while True:
        try:
            if vencida():
                rodar_todas()
        except Exception as e:                      # nunca derrubar a thread
            db.log_event("reconsulta_erro", payload={"erro": instagram.sem_segredo(e)[:300]})
        time.sleep(checar_a_cada_s)
