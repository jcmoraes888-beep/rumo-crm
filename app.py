"""Rumo CRM — CRM para pequenos negócios em Streamlit.

Rodar localmente:  streamlit run app.py
"""
import streamlit as st

from crm import auth, db
from crm.ui import estilo, mostrar_aviso

st.set_page_config(page_title="Rumo CRM", page_icon="🧭", layout="wide")
estilo()

nome_empresa = db.get_config("empresa", "") or "Rumo CRM"

if not auth.usuario_atual():
    auth.tela_acesso(nome_empresa)
    st.stop()

paginas = {
    "painel": st.Page("views/painel.py", title="Painel", icon="📊", default=True),
    "funil": st.Page("views/funil.py", title="Funil", icon="🧲"),
    "contatos": st.Page("views/contatos.py", title="Contatos", icon="👥"),
    "tarefas": st.Page("views/tarefas.py", title="Tarefas", icon="✅"),
    "ajustes": st.Page("views/ajustes.py", title="Ajustes", icon="⚙️"),
}
st.session_state["_pg_contatos"] = paginas["contatos"]

with st.sidebar:
    st.markdown(f"### {nome_empresa}")
    u = auth.usuario_atual()
    st.caption(f"{u['nome']} · {'Administrador' if u['papel'] == 'admin' else 'Vendedor'}")
    if st.button("➕ Novo contato", type="primary", width="stretch"):
        from crm.ui import dialog_contato
        dialog_contato()

nav = st.navigation(list(paginas.values()))

with st.sidebar:
    st.divider()
    if st.button("Sair", width="stretch"):
        auth.sair()

if st.session_state.pop("ir_para_contato", False) and nav.url_path != paginas["contatos"].url_path:
    st.switch_page(paginas["contatos"])

mostrar_aviso()
nav.run()
