import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crm import db
from crm.config import ABERTAS, ETAPA_COR, ETAPA_IDS, ETAPA_NOME, brl, hoje, rotulo_prazo
from crm.seed import carregar_exemplos
from crm.ui import abrir_contato, filtrar_meus, nomes_usuarios
from crm.auth import usuario_atual

st.title("Painel")

df = filtrar_meus(db.listar_contatos())
atv = db.listar_atividades()
atv = atv[atv["contato_id"].isin(df["id"])]

if df.empty:
    st.info("Nenhum contato cadastrado ainda. Use **➕ Novo contato** na barra lateral para começar.")
    if st.button("Carregar dados de exemplo"):
        carregar_exemplos(usuario_atual()["id"])
        st.rerun()
    st.stop()

# ---- Filtro de responsável ----
usuarios = nomes_usuarios()
resp_ids = sorted({int(x) for x in df["responsavel_id"].dropna()})
if len(resp_ids) > 1:
    escolha = st.selectbox("Responsável", [0] + resp_ids, format_func=lambda i: "Toda a equipe" if i == 0 else usuarios.get(i, "?"))
    if escolha:
        df = df[df["responsavel_id"] == escolha]
        atv = atv[atv["contato_id"].isin(df["id"])]

abertos = df[df["etapa"].isin(ABERTAS)]
ganhos = df[df["etapa"] == "ganho"]
perdidos = df[df["etapa"] == "perdido"]
h = hoje()
ganho_em = pd.to_datetime(ganhos["ganho_em"])
ganho_mes = ganhos[(ganho_em.dt.year == h.year) & (ganho_em.dt.month == h.month)]
fechados = len(ganhos) + len(perdidos)
conv = f"{100 * len(ganhos) / fechados:.0f}%" if fechados else "—"
ticket = brl(ganhos["valor"].mean()) if len(ganhos) else "—"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Oportunidades abertas", len(abertos), border=True)
k2.metric("Valor em negociação", brl(abertos["valor"].sum()), border=True)
k3.metric("Fechado no mês", brl(ganho_mes["valor"].sum()), f"{len(ganho_mes)} venda(s)", delta_color="off", delta_arrow="off", border=True)
k4.metric("Taxa de conversão", conv, f"ticket médio {ticket}", delta_color="off", delta_arrow="off", border=True)

esq, dir_ = st.columns([3, 2], gap="large")

with esq:
    st.subheader("Funil por etapa")
    resumo = (df.groupby("etapa").agg(qtd=("id", "count"), valor=("valor", "sum"))
              .reindex(ETAPA_IDS, fill_value=0).reset_index())
    resumo["nome"] = resumo["etapa"].map(ETAPA_NOME)
    fig = go.Figure(go.Bar(
        x=resumo["qtd"], y=resumo["nome"], orientation="h",
        marker_color=[ETAPA_COR[e] for e in resumo["etapa"]],
        text=[f"{q} · {brl(v)}" for q, v in zip(resumo["qtd"], resumo["valor"])], textposition="outside",
        hovertemplate="%{y}: %{x} contato(s)<extra></extra>", cliponaxis=False,
    ))
    fig.update_layout(height=300, margin=dict(l=10, r=90, t=10, b=10), yaxis=dict(autorange="reversed"),
                      xaxis=dict(visible=False), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, config={"displayModeBar": False})

    st.subheader("Origem dos contatos")
    orig = df.groupby("origem").agg(contatos=("id", "count"),
                                   ganhos=("etapa", lambda s: (s == "ganho").sum())).sort_values("contatos", ascending=False)
    fig2 = go.Figure()
    fig2.add_bar(y=orig.index, x=orig["contatos"], orientation="h", name="Contatos", marker_color="#9DB0E6")
    fig2.add_bar(y=orig.index, x=orig["ganhos"], orientation="h", name="Ganhos", marker_color="#1C7C4E")
    fig2.update_layout(barmode="overlay", height=60 + 34 * len(orig), margin=dict(l=10, r=10, t=10, b=10),
                       yaxis=dict(autorange="reversed"), xaxis=dict(dtick=1), legend=dict(orientation="h", y=-0.15),
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, config={"displayModeBar": False})

with dir_:
    pend = atv[(atv["tarefa"] == True) & (atv["feita"] == False) & atv["vence"].notna()].sort_values("vence")  # noqa: E712
    atrasadas = (pend["vence"] < h).sum()
    st.subheader("Próximas tarefas")
    if atrasadas:
        st.error(f"{atrasadas} tarefa(s) atrasada(s)")
    if pend.empty:
        st.caption("Nenhuma tarefa pendente.")
    nomes = dict(zip(df["id"], df["nome"]))
    for _, t in pend.head(8).iterrows():
        with st.container(border=True):
            st.caption(rotulo_prazo(t["vence"]))
            st.write(t["texto"])
            if st.button(nomes.get(t["contato_id"], "Contato"), key=f"p_{t['id']}", type="tertiary"):
                abrir_contato(t["contato_id"])
    if len(pend) > 8:
        st.page_link("views/tarefas.py", label=f"Ver todas as {len(pend)} tarefas →")
