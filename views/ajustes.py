import streamlit as st

from crm import db
from crm.auth import eh_admin, gerar_hash, usuario_atual, conferir
from crm.seed import carregar_exemplos

st.title("Ajustes")

eu = usuario_atual()

# ---- Minha senha (todos) ----
with st.expander("Trocar minha senha"):
    with st.form("minha_senha", clear_on_submit=True):
        atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha (mínimo 8 caracteres)", type="password")
        if st.form_submit_button("Salvar nova senha"):
            u = db.usuario_por_email(eu["email"])
            if not conferir(atual, u["senha_hash"]):
                st.error("Senha atual incorreta.")
            elif len(nova) < 8:
                st.error("A nova senha precisa ter pelo menos 8 caracteres.")
            else:
                db.atualizar_usuario(eu["id"], senha_hash=gerar_hash(nova))
                st.success("Senha alterada.")

if not eh_admin():
    st.caption("As demais configurações são feitas pelo administrador.")
    st.stop()

# ---- Empresa ----
st.subheader("Empresa")
with st.form("empresa"):
    nome = st.text_input("Nome exibido no sistema", value=db.get_config("empresa", ""), placeholder="Ex.: Padaria Trigo Bom")
    ve_tudo = st.toggle("Vendedores veem os contatos de toda a equipe",
                        value=db.get_config("vendedor_ve_tudo", "1") == "1",
                        help="Desligado: cada vendedor vê só os contatos em que é responsável.")
    if st.form_submit_button("Salvar", type="primary"):
        db.set_config("empresa", nome.strip())
        db.set_config("vendedor_ve_tudo", "1" if ve_tudo else "0")
        st.session_state["aviso"] = "Ajustes salvos."
        st.rerun()

# ---- Usuários ----
st.subheader("Usuários")
us = db.listar_usuarios()
st.dataframe(
    us.assign(papel=us["papel"].map({"admin": "Administrador", "vendedor": "Vendedor"}),
              ativo=us["ativo"].map({True: "Ativo", False: "Desativado"}))
      .rename(columns={"nome": "Nome", "email": "E-mail", "papel": "Perfil", "ativo": "Situação"})
      .drop(columns="id"),
    hide_index=True,
)

a, b = st.columns(2, gap="large")
with a:
    st.markdown("**Adicionar usuário**")
    with st.form("novo_usuario", clear_on_submit=True):
        n = st.text_input("Nome")
        e = st.text_input("E-mail")
        s = st.text_input("Senha inicial (mínimo 8 caracteres)", type="password")
        p = st.selectbox("Perfil", ["vendedor", "admin"], format_func={"vendedor": "Vendedor", "admin": "Administrador"}.get)
        if st.form_submit_button("Adicionar"):
            if not n.strip() or "@" not in e:
                st.error("Preencha nome e um e-mail válido.")
            elif len(s) < 8:
                st.error("A senha precisa ter pelo menos 8 caracteres.")
            elif db.usuario_por_email(e):
                st.error("Já existe um usuário com esse e-mail.")
            else:
                db.criar_usuario(n, e, gerar_hash(s), p)
                st.session_state["aviso"] = f"Usuário {n.strip()} adicionado."
                st.rerun()
with b:
    st.markdown("**Alterar usuário**")
    outros = us[us["id"] != eu["id"]]
    if outros.empty:
        st.caption("Nenhum outro usuário cadastrado.")
    else:
        uid = st.selectbox("Usuário", outros["id"], format_func=dict(zip(outros["id"], outros["nome"])).get)
        linha = outros[outros["id"] == uid].iloc[0]
        with st.form("alt_usuario", clear_on_submit=True):
            ativo = st.toggle("Ativo (pode entrar no sistema)", value=bool(linha["ativo"]))
            senha = st.text_input("Redefinir senha (deixe em branco para manter)", type="password")
            if st.form_submit_button("Salvar alterações"):
                campos = {"ativo": ativo}
                if senha:
                    if len(senha) < 8:
                        st.error("A senha precisa ter pelo menos 8 caracteres.")
                        st.stop()
                    campos["senha_hash"] = gerar_hash(senha)
                db.atualizar_usuario(int(uid), **campos)
                st.session_state["aviso"] = "Usuário atualizado."
                st.rerun()

# ---- Dados de exemplo ----
st.subheader("Dados de exemplo")
n_ex = db.contar_exemplos()
if n_ex:
    st.write(f"Há **{n_ex}** contato(s) de exemplo no sistema.")
    with st.popover("Remover exemplos"):
        st.write("Remove todos os contatos e atividades marcados como exemplo. Seus dados reais não são afetados.")
        if st.button("Confirmar remoção", type="primary"):
            db.remover_exemplos()
            st.session_state["aviso"] = "Exemplos removidos."
            st.rerun()
else:
    st.caption("Útil para demonstrar o sistema a um cliente.")
    if st.button("Carregar dados de exemplo"):
        carregar_exemplos(eu["id"])
        st.session_state["aviso"] = "Exemplos carregados."
        st.rerun()
