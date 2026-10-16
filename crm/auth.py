"""Login simples com senha protegida por PBKDF2 (biblioteca padrão do Python)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

import streamlit as st

from . import db

ITERACOES = 240_000


def gerar_hash(senha: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), ITERACOES).hex()
    return f"pbkdf2${ITERACOES}${sal}${h}"


def conferir(senha: str, guardado: str) -> bool:
    try:
        _, it, sal, h = guardado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), int(it)).hex()
        return hmac.compare_digest(calc, h)
    except Exception:
        return False


def usuario_atual() -> dict | None:
    return st.session_state.get("usuario")


def eh_admin() -> bool:
    u = usuario_atual()
    return bool(u and u["papel"] == "admin")


def sair() -> None:
    st.session_state.pop("usuario", None)
    st.rerun()


def tela_acesso(nome_empresa: str) -> None:
    """Mostra o primeiro cadastro (se o banco estiver vazio) ou o login."""
    _, meio, _ = st.columns([1, 1.4, 1])
    with meio:
        st.title(nome_empresa)
        if db.contar_usuarios() == 0:
            st.subheader("Configuração inicial")
            st.caption("Crie o usuário administrador. Ele poderá cadastrar os demais usuários em Ajustes.")
            with st.form("primeiro_admin"):
                nome = st.text_input("Seu nome")
                email = st.text_input("E-mail")
                s1 = st.text_input("Senha (mínimo 8 caracteres)", type="password")
                s2 = st.text_input("Repita a senha", type="password")
                if st.form_submit_button("Criar administrador", type="primary", width="stretch"):
                    if not nome.strip() or "@" not in email:
                        st.error("Preencha nome e um e-mail válido.")
                    elif len(s1) < 8:
                        st.error("A senha precisa ter pelo menos 8 caracteres.")
                    elif s1 != s2:
                        st.error("As senhas não conferem.")
                    else:
                        uid = db.criar_usuario(nome, email, gerar_hash(s1), papel="admin")
                        st.session_state["usuario"] = {"id": uid, "nome": nome.strip(), "email": email.strip().lower(), "papel": "admin"}
                        st.rerun()
            return

        st.subheader("Entrar")
        with st.form("login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary", width="stretch"):
                u = db.usuario_por_email(email) if email else None
                if u and u["ativo"] and conferir(senha, u["senha_hash"]):
                    st.session_state["usuario"] = {"id": u["id"], "nome": u["nome"], "email": u["email"], "papel": u["papel"]}
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

        _esqueci_senha()


MAX_TENTATIVAS = 5


def _esqueci_senha() -> None:
    """Redefine a senha com a chave de recuperação guardada nos Secrets do app."""
    chave = db.chave_recuperacao()
    with st.expander("Esqueci minha senha"):
        if not chave:
            st.caption("Peça ao administrador para redefinir sua senha em **Ajustes → Alterar usuário**.")
            return
        tentativas = st.session_state.get("_tentativas_recuperacao", 0)
        if tentativas >= MAX_TENTATIVAS:
            st.error("Muitas tentativas. Recarregue a página para tentar de novo.")
            return
        st.caption("Informe a chave de recuperação, que fica em Manage app → Settings → Secrets.")
        with st.form("recuperar_senha", clear_on_submit=True):
            email = st.text_input("E-mail")
            chave_digitada = st.text_input("Chave de recuperação", type="password")
            s1 = st.text_input("Nova senha (mínimo 8 caracteres)", type="password")
            s2 = st.text_input("Repita a nova senha", type="password")
            if st.form_submit_button("Redefinir senha", width="stretch"):
                u = db.usuario_por_email(email) if email.strip() else None
                if not hmac.compare_digest(chave_digitada.strip().encode(), chave.encode()) or not u:
                    st.session_state["_tentativas_recuperacao"] = tentativas + 1
                    st.error("E-mail ou chave de recuperação incorretos.")
                elif len(s1) < 8:
                    st.error("A nova senha precisa ter pelo menos 8 caracteres.")
                elif s1 != s2:
                    st.error("As senhas não conferem.")
                else:
                    db.atualizar_usuario(u["id"], senha_hash=gerar_hash(s1), ativo=True)
                    st.session_state.pop("_tentativas_recuperacao", None)
                    st.success("Senha redefinida. Entre com o e-mail e a nova senha.")
