"""Componentes de interface reutilizados pelas páginas."""
from __future__ import annotations

import re
from datetime import timedelta

import pandas as pd
import streamlit as st

from . import db
from .auth import eh_admin, usuario_atual
from .config import ABERTAS, ETAPA_COR, ETAPA_IDS, ETAPA_NOME, ORIGENS, TIPOS, brl, data_br, hoje, rotulo_prazo

CSS = """
<style>
.block-container {padding-top: 2rem;}
.etapa-pill {display:inline-block;padding:1px 10px;border-radius:99px;font-size:.82rem;font-weight:600;color:#fff;white-space:nowrap}
.kpi-sub {color: var(--text-color); opacity:.65; font-size:.85rem; margin-top:-.6rem}
.card-nome {font-weight:600; line-height:1.25}
.card-emp {opacity:.7; font-size:.86rem}
.card-val {font-variant-numeric: tabular-nums; font-size:.9rem}
.tag-ex {font-size:.72rem; border:1px dashed rgba(128,128,128,.6); border-radius:4px; padding:0 5px; opacity:.8}
.col-head {border-top:4px solid var(--c); padding-top:.4rem; margin-bottom:.4rem}
</style>
"""


def estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def pill(etapa: str) -> str:
    return f'<span class="etapa-pill" style="background:{ETAPA_COR.get(etapa, "#888")}">{ETAPA_NOME.get(etapa, etapa)}</span>'


def nomes_usuarios() -> dict[int, str]:
    df = db.listar_usuarios()
    return dict(zip(df["id"], df["nome"]))


def abrir_contato(cid: int) -> None:
    """Abre a ficha do contato na página Contatos."""
    st.session_state["contato_aberto"] = int(cid)
    st.switch_page(st.session_state["_pg_contatos"])


def proximas_tarefas(atv: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por contato com a tarefa pendente mais próxima."""
    p = atv[(atv["tarefa"] == True) & (atv["feita"] == False) & atv["vence"].notna()]  # noqa: E712
    if p.empty:
        return pd.DataFrame(columns=["contato_id", "vence", "texto"])
    return p.sort_values("vence").groupby("contato_id", as_index=False).first()[["contato_id", "vence", "texto"]]


# ---------------- Formulário de contato ----------------
@st.dialog("Contato", width="large")
def dialog_contato(cid: int | None = None) -> None:
    c = dict(db.obter_contato(cid)) if cid else {"etapa": "novo", "origem": "Indicação", "valor": 0.0}
    usuarios = db.listar_usuarios(apenas_ativos=True)
    eu = usuario_atual()
    with st.form("form_contato", border=False):
        nome = st.text_input("Nome *", value=c.get("nome", ""))
        empresa = st.text_input("Empresa", value=c.get("empresa", "") or "")
        a, b = st.columns(2)
        telefone = a.text_input("Telefone / WhatsApp", value=c.get("telefone", "") or "", placeholder="(45) 99999-0000")
        email = b.text_input("E-mail", value=c.get("email", "") or "")
        origem = a.selectbox("Origem", ORIGENS, index=ORIGENS.index(c["origem"]) if c.get("origem") in ORIGENS else 0)
        etapa = b.selectbox("Etapa", ETAPA_IDS, index=ETAPA_IDS.index(c.get("etapa", "novo")), format_func=ETAPA_NOME.get)
        valor = a.number_input("Valor estimado (R$)", min_value=0.0, step=100.0, value=float(c.get("valor") or 0))
        ids = usuarios["id"].tolist()
        resp_atual = c.get("responsavel_id") or eu["id"]
        responsavel = b.selectbox("Responsável", ids, index=ids.index(resp_atual) if resp_atual in ids else 0,
                                  format_func=dict(zip(usuarios["id"], usuarios["nome"])).get)
        motivo = st.text_input("Motivo da perda (se perdido)", value=c.get("motivo_perda", "") or "")
        notas = st.text_area("Notas", value=c.get("notas", "") or "")
        if st.form_submit_button("Salvar contato", type="primary"):
            if not nome.strip():
                st.error("Informe o nome do contato.")
                return
            dados = dict(nome=nome.strip(), empresa=empresa.strip(), telefone=telefone.strip(), email=email.strip(),
                         origem=origem, etapa=etapa, valor=float(valor), responsavel_id=int(responsavel),
                         notas=notas.strip(), motivo_perda=motivo.strip())
            if cid:
                db.atualizar_contato(cid, **dados)
                st.session_state["aviso"] = "Contato atualizado."
            else:
                novo = db.criar_contato(**dados)
                st.session_state["contato_aberto"] = novo
                st.session_state["ir_para_contato"] = True
                st.session_state["aviso"] = "Contato cadastrado."
            st.rerun()


# ---------------- Ficha do contato ----------------
def ficha_contato(cid: int) -> None:
    c = db.obter_contato(cid)
    if not c:
        st.session_state.pop("contato_aberto", None)
        st.warning("Este contato não existe mais.")
        return
    eu = usuario_atual()
    usuarios = nomes_usuarios()

    topo, acoes = st.columns([3, 2], vertical_alignment="bottom")
    with topo:
        if st.button("← Voltar para a lista"):
            st.session_state.pop("contato_aberto", None)
            st.rerun()
        ex = ' <span class="tag-ex">exemplo</span>' if c["exemplo"] else ""
        st.markdown(f"## {c['nome']}{ex}", unsafe_allow_html=True)
        st.markdown(f"{c['empresa'] or ''} &nbsp; {pill(c['etapa'])}", unsafe_allow_html=True)
    with acoes:
        b1, b2 = st.columns(2)
        if b1.button("✏️ Editar", width="stretch"):
            dialog_contato(cid)
        with b2.popover("🗑️ Excluir", width="stretch"):
            st.write(f"Excluir **{c['nome']}** e todo o histórico? Não dá para desfazer.")
            if st.button("Confirmar exclusão", type="primary"):
                db.excluir_contato(cid)
                st.session_state.pop("contato_aberto", None)
                st.session_state["aviso"] = "Contato excluído."
                st.rerun()

    st.write("")
    nova = st.segmented_control("Etapa do funil", ETAPA_IDS, default=c["etapa"], format_func=ETAPA_NOME.get,
                                key=f"etapa_{cid}_{c['etapa']}")
    if nova and nova != c["etapa"]:
        db.atualizar_contato(cid, etapa=nova)
        st.session_state["aviso"] = f"Movido para {ETAPA_NOME[nova]}."
        st.rerun()

    esq, dir_ = st.columns([2, 3], gap="large")
    with esq:
        st.markdown("#### Dados")
        st.markdown(f"**Valor:** {brl(c['valor'])}")
        tel = c["telefone"] or ""
        st.markdown(f"**Telefone:** {tel or '—'}")
        digitos = re.sub(r"\D", "", tel)
        if len(digitos) >= 10:
            num = "55" + digitos if len(digitos) <= 11 else digitos
            st.link_button("Abrir no WhatsApp", f"https://wa.me/{num}")
        st.markdown(f"**E-mail:** {c['email'] or '—'}")
        st.markdown(f"**Origem:** {c['origem'] or '—'}")
        st.markdown(f"**Responsável:** {usuarios.get(c['responsavel_id'], '—')}")
        st.markdown(f"**Cadastro:** {data_br(c['criado_em'])}")
        if c["etapa"] == "ganho" and c["ganho_em"]:
            st.markdown(f"**Ganho em:** {data_br(c['ganho_em'])}")
        if c["etapa"] == "perdido" and c["motivo_perda"]:
            st.markdown(f"**Motivo da perda:** {c['motivo_perda']}")
        if c["notas"]:
            st.markdown("**Notas:**")
            st.text(c["notas"])

    with dir_:
        st.markdown("#### Registrar interação")
        with st.form(f"nova_atv_{cid}", clear_on_submit=True):
            a, b = st.columns(2)
            tipo = a.selectbox("Tipo", list(TIPOS), format_func=TIPOS.get)
            eh_tarefa = b.toggle("Agendar como tarefa")
            vence = b.date_input("Data da tarefa", value=hoje() + timedelta(days=1), format="DD/MM/YYYY")
            texto = st.text_area("Descrição", placeholder="O que aconteceu ou o que precisa ser feito?")
            if st.form_submit_button("Registrar", type="primary"):
                if not texto.strip():
                    st.error("Escreva a descrição.")
                else:
                    db.criar_atividade(cid, tipo, texto, tarefa=eh_tarefa, vence=vence, usuario_id=eu["id"])
                    st.session_state["aviso"] = "Tarefa agendada." if eh_tarefa else "Interação registrada."
                    st.rerun()

        st.markdown("#### Histórico e tarefas")
        atv = db.listar_atividades(cid)
        if atv.empty:
            st.caption("Nenhuma interação registrada ainda.")
        pend = atv[(atv["tarefa"] == True) & (atv["feita"] == False)].sort_values("vence")  # noqa: E712
        resto = atv.drop(pend.index)
        for _, a in pd.concat([pend, resto]).iterrows():
            with st.container(border=True):
                l, r = st.columns([5, 1], vertical_alignment="center")
                with l:
                    if a["tarefa"] and not a["feita"]:
                        meta = f"{TIPOS.get(a['tipo'], '')} · {rotulo_prazo(a['vence'])}"
                    elif a["tarefa"]:
                        meta = f"{TIPOS.get(a['tipo'], '')} · ✅ concluída"
                    else:
                        meta = f"{TIPOS.get(a['tipo'], '')} · {a['data']:%d/%m/%Y %H:%M}"
                    autor = usuarios.get(a["usuario_id"])
                    st.caption(meta + (f" · {autor}" if autor else ""))
                    st.write(a["texto"])
                with r:
                    if a["tarefa"]:
                        feito = st.checkbox("Feita", value=bool(a["feita"]), key=f"chk_{a['id']}")
                        if feito != bool(a["feita"]):
                            db.marcar_tarefa(int(a["id"]), feito)
                            st.rerun()
                    if st.button("✕", key=f"del_{a['id']}", help="Remover registro"):
                        db.excluir_atividade(int(a["id"]))
                        st.rerun()


def mostrar_aviso() -> None:
    msg = st.session_state.pop("aviso", None)
    if msg:
        st.toast(msg)


def pode_ver_tudo() -> bool:
    return eh_admin()


def filtrar_meus(df: pd.DataFrame, coluna: str = "responsavel_id") -> pd.DataFrame:
    """Vendedor vê só os próprios contatos se a opção estiver ligada em Ajustes."""
    if eh_admin() or db.get_config("vendedor_ve_tudo", "1") == "1":
        return df
    return df[df[coluna] == usuario_atual()["id"]]


__all__ = ["estilo", "pill", "abrir_contato", "dialog_contato", "ficha_contato", "mostrar_aviso",
           "proximas_tarefas", "nomes_usuarios", "filtrar_meus", "ABERTAS"]
