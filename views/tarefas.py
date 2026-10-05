import streamlit as st

from crm import db
from crm.auth import usuario_atual
from crm.config import TIPOS, data_br, hoje, rotulo_prazo
from crm.ui import abrir_contato, filtrar_meus, nomes_usuarios

st.title("Tarefas")

contatos = filtrar_meus(db.listar_contatos())
nomes = dict(zip(contatos["id"], contatos["nome"]))
atv = db.listar_atividades()
atv = atv[(atv["tarefa"] == True) & atv["contato_id"].isin(contatos["id"])]  # noqa: E712

usuarios = nomes_usuarios()
so_minhas = st.toggle("Só as minhas tarefas", value=False)
if so_minhas:
    atv = atv[atv["usuario_id"] == usuario_atual()["id"]]

h = hoje()
pend = atv[atv["feita"] == False].sort_values("vence")  # noqa: E712
grupos = [
    ("🔴 Atrasadas", pend[pend["vence"] < h]),
    ("🟠 Hoje", pend[pend["vence"] == h]),
    ("⚪ Próximas", pend[pend["vence"] > h]),
]
feitas = atv[atv["feita"] == True].sort_values("feita_em", ascending=False).head(10)  # noqa: E712


def concluir(aid: int, valor: bool) -> None:
    db.marcar_tarefa(aid, valor)
    st.session_state["aviso"] = "Tarefa concluída." if valor else "Tarefa reaberta."


def linha(t, feita: bool = False) -> None:
    with st.container(border=True):
        a, b, c = st.columns([0.6, 6, 2.4], vertical_alignment="center")
        a.checkbox("Concluir", value=feita, key=f"t_{t['id']}", label_visibility="collapsed",
                   on_change=concluir, args=(int(t["id"]), not feita))
        with b:
            st.write(f"~~{t['texto']}~~" if feita else t["texto"])
            resp = usuarios.get(t["usuario_id"])
            st.caption(f"{TIPOS.get(t['tipo'], '')}" + (f" · {resp}" if resp else ""))
        with c:
            if st.button(nomes.get(t["contato_id"], "Contato"), key=f"c_{t['id']}", type="tertiary"):
                abrir_contato(t["contato_id"])
            st.caption(f"Concluída {data_br(t['feita_em'])}" if feita else rotulo_prazo(t["vence"]))


k = st.columns(3)
for col, (titulo, g) in zip(k, grupos):
    col.metric(titulo, len(g), border=True)

if pend.empty:
    st.success("Nenhuma tarefa pendente. Agende tarefas pela ficha de cada contato.")

for titulo, g in grupos:
    if not g.empty:
        st.subheader(f"{titulo} · {len(g)}")
        for _, t in g.iterrows():
            linha(t)

if not feitas.empty:
    with st.expander(f"Concluídas recentemente ({len(feitas)})"):
        for _, t in feitas.iterrows():
            linha(t, feita=True)
