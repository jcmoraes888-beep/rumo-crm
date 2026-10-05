import streamlit as st

from crm import db
from crm.config import ABERTAS, ETAPA_COR, ETAPA_IDS, ETAPA_NOME, brl, rotulo_prazo
from crm.ui import abrir_contato, filtrar_meus, proximas_tarefas


def mover(cid: int, etapa: str) -> None:
    db.atualizar_contato(cid, etapa=etapa)
    st.session_state["aviso"] = f"Movido para {ETAPA_NOME[etapa]}."


st.title("Funil de vendas")

df = filtrar_meus(db.listar_contatos())
if df.empty:
    st.info("Nenhum contato no funil ainda. Use **➕ Novo contato** na barra lateral.")
    st.stop()

c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
busca = c1.text_input("Filtrar", placeholder="Nome ou empresa", label_visibility="collapsed")
todas = c2.toggle("Mostrar ganhos e perdidos", value=False)
st.caption("Clique no nome para abrir a ficha. Use ◀ ▶ para mover o contato de etapa.")

if busca:
    b = busca.lower()
    df = df[df["nome"].str.lower().str.contains(b, regex=False) | df["empresa"].fillna("").str.lower().str.contains(b, regex=False)]

prox = proximas_tarefas(db.listar_atividades()).set_index("contato_id")["vence"].to_dict()
etapas = ETAPA_IDS if todas else ABERTAS
cols = st.columns(len(etapas), gap="small")

for col, etapa in zip(cols, etapas):
    sub = df[df["etapa"] == etapa].sort_values("valor", ascending=False)
    with col:
        st.markdown(
            f'<div class="col-head" style="--c:{ETAPA_COR[etapa]}"><b>{ETAPA_NOME[etapa]}</b><br>'
            f'<span class="card-emp">{len(sub)} · {brl(sub["valor"].sum())}</span></div>',
            unsafe_allow_html=True)
        if sub.empty:
            st.caption("Nenhum contato")
        for _, c in sub.iterrows():
            cid = int(c["id"])
            with st.container(border=True):
                if st.button(c["nome"], key=f"abrir_{cid}", type="tertiary"):
                    abrir_contato(cid)
                ex = ' <span class="tag-ex">exemplo</span>' if c["exemplo"] else ""
                st.markdown(f'<div class="card-emp">{c["empresa"] or ""}{ex}</div>'
                            f'<div class="card-val">{brl(c["valor"])}</div>', unsafe_allow_html=True)
                if cid in prox:
                    st.caption(rotulo_prazo(prox[cid]))
                i = ABERTAS.index(etapa) if etapa in ABERTAS else len(ABERTAS)
                anterior = ABERTAS[i - 1] if i > 0 else None
                seguinte = ABERTAS[i + 1] if i + 1 < len(ABERTAS) else None
                a, b = st.columns(2)
                if anterior:
                    a.button("◀", key=f"ant_{cid}", help=f"Voltar para {ETAPA_NOME[anterior]}",
                             on_click=mover, args=(cid, anterior), width="stretch")
                if seguinte:
                    b.button("▶", key=f"prox_{cid}", help=f"Avançar para {ETAPA_NOME[seguinte]}",
                             on_click=mover, args=(cid, seguinte), width="stretch")
                if etapa == "negociacao":
                    g, p = st.columns(2)
                    g.button("Ganho", key=f"g_{cid}", on_click=mover, args=(cid, "ganho"), width="stretch")
                    p.button("Perdido", key=f"l_{cid}", on_click=mover, args=(cid, "perdido"), width="stretch")
