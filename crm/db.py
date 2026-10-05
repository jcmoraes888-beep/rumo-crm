"""Camada de dados (SQLAlchemy Core).

Funciona com SQLite (padrão, arquivo local) ou PostgreSQL (Neon, Supabase etc.)
informando DATABASE_URL nos Secrets do Streamlit ou em variável de ambiente.
"""
from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, MetaData, String,
    Table, Text, create_engine, delete, func, insert, select, update,
)
from sqlalchemy.engine import Engine

from .config import agora

meta = MetaData()
_ERRO_SECRETS: list[str] = []

usuarios = Table(
    "usuarios", meta,
    Column("id", Integer, primary_key=True),
    Column("nome", String(120), nullable=False),
    Column("email", String(200), nullable=False, unique=True),
    Column("senha_hash", String(300), nullable=False),
    Column("papel", String(20), nullable=False, default="vendedor"),  # admin | vendedor
    Column("ativo", Boolean, nullable=False, default=True),
    Column("criado_em", DateTime, nullable=False),
)

contatos = Table(
    "contatos", meta,
    Column("id", Integer, primary_key=True),
    Column("nome", String(160), nullable=False),
    Column("empresa", String(160), default=""),
    Column("telefone", String(40), default=""),
    Column("email", String(200), default=""),
    Column("origem", String(40), default="Outro"),
    Column("etapa", String(20), nullable=False, default="novo"),
    Column("valor", Float, default=0),
    Column("responsavel_id", Integer, ForeignKey("usuarios.id"), nullable=True),
    Column("notas", Text, default=""),
    Column("motivo_perda", String(200), default=""),
    Column("exemplo", Boolean, nullable=False, default=False),
    Column("criado_em", DateTime, nullable=False),
    Column("atualizado_em", DateTime, nullable=False),
    Column("ganho_em", DateTime, nullable=True),
)

atividades = Table(
    "atividades", meta,
    Column("id", Integer, primary_key=True),
    Column("contato_id", Integer, ForeignKey("contatos.id", ondelete="CASCADE"), nullable=False),
    Column("tipo", String(20), nullable=False),
    Column("texto", Text, nullable=False),
    Column("data", DateTime, nullable=False),
    Column("tarefa", Boolean, nullable=False, default=False),
    Column("vence", Date, nullable=True),
    Column("feita", Boolean, nullable=False, default=False),
    Column("feita_em", DateTime, nullable=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=True),
    Column("exemplo", Boolean, nullable=False, default=False),
)

config_tb = Table(
    "config", meta,
    Column("chave", String(60), primary_key=True),
    Column("valor", Text, default=""),
)


def _database_url() -> str:
    try:
        url = st.secrets.get("DATABASE_URL")
    except Exception as e:  # sem secrets.toml (uso local) ou com erro de formatação
        _ERRO_SECRETS.append(str(e))
        url = None
    url = url or os.environ.get("DATABASE_URL") or "sqlite:///rumo_crm.db"
    # Neon/Heroku às vezes entregam "postgres://"; o SQLAlchemy espera "postgresql://"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # usa sempre o driver psycopg (versão 3), o mesmo do requirements.txt
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@st.cache_resource
def engine() -> Engine:
    url = _database_url()
    kw = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    eng = create_engine(url, **kw)
    meta.create_all(eng)
    return eng


def usando_sqlite() -> bool:
    return engine().dialect.name == "sqlite"


def na_nuvem() -> bool:
    """True quando roda no Streamlit Community Cloud."""
    return os.path.isdir("/mount/src")


def aviso_banco() -> None:
    """Avisa quando o app está na nuvem sem banco permanente configurado."""
    if na_nuvem() and usando_sqlite():
        erro = _ERRO_SECRETS[-1] if _ERRO_SECRETS else ""
        st.error(
            "**Banco de dados temporário em uso.** O `DATABASE_URL` não foi encontrado nos Secrets, "
            "então tudo o que for cadastrado será apagado quando o app reiniciar. "
            "Em Manage app → Settings → Secrets, use exatamente o formato:\n\n"
            '`DATABASE_URL = "postgresql://usuario:senha@host/banco?sslmode=require"`'
            + (f"\n\nErro ao ler os Secrets: `{erro}`" if erro else "")
        )


# ---------------- Usuários ----------------
def contar_usuarios() -> int:
    with engine().connect() as c:
        return c.execute(select(func.count()).select_from(usuarios)).scalar_one()


def usuario_por_email(email: str):
    with engine().connect() as c:
        return c.execute(select(usuarios).where(func.lower(usuarios.c.email) == email.strip().lower())).mappings().first()


def criar_usuario(nome: str, email: str, senha_hash: str, papel: str = "vendedor") -> int:
    with engine().begin() as c:
        r = c.execute(insert(usuarios).values(
            nome=nome.strip(), email=email.strip().lower(), senha_hash=senha_hash,
            papel=papel, ativo=True, criado_em=agora()))
        return r.inserted_primary_key[0]


def atualizar_usuario(uid: int, **campos) -> None:
    with engine().begin() as c:
        c.execute(update(usuarios).where(usuarios.c.id == uid).values(**campos))


def listar_usuarios(apenas_ativos: bool = False) -> pd.DataFrame:
    q = select(usuarios.c.id, usuarios.c.nome, usuarios.c.email, usuarios.c.papel, usuarios.c.ativo).order_by(usuarios.c.nome)
    if apenas_ativos:
        q = q.where(usuarios.c.ativo.is_(True))
    with engine().connect() as c:
        return pd.DataFrame(c.execute(q).mappings().all(), columns=["id", "nome", "email", "papel", "ativo"])


# ---------------- Contatos ----------------
COLS_CONTATO = ["id", "nome", "empresa", "telefone", "email", "origem", "etapa", "valor", "responsavel_id",
                "notas", "motivo_perda", "exemplo", "criado_em", "atualizado_em", "ganho_em"]


def listar_contatos() -> pd.DataFrame:
    with engine().connect() as c:
        rows = c.execute(select(contatos).order_by(contatos.c.criado_em.desc())).mappings().all()
    df = pd.DataFrame(rows, columns=COLS_CONTATO)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    return df


def obter_contato(cid: int):
    with engine().connect() as c:
        return c.execute(select(contatos).where(contatos.c.id == cid)).mappings().first()


def criar_contato(**dados) -> int:
    t = agora()
    dados.setdefault("criado_em", t)
    dados.setdefault("atualizado_em", t)
    if dados.get("etapa") == "ganho" and not dados.get("ganho_em"):
        dados["ganho_em"] = t
    with engine().begin() as c:
        return c.execute(insert(contatos).values(**dados)).inserted_primary_key[0]


def atualizar_contato(cid: int, **dados) -> None:
    dados["atualizado_em"] = agora()
    with engine().begin() as c:
        if "etapa" in dados:
            atual = c.execute(select(contatos.c.etapa).where(contatos.c.id == cid)).scalar_one_or_none()
            if dados["etapa"] == "ganho" and atual != "ganho":
                dados["ganho_em"] = agora()
            elif dados["etapa"] != "ganho":
                dados["ganho_em"] = None
        c.execute(update(contatos).where(contatos.c.id == cid).values(**dados))


def excluir_contato(cid: int) -> None:
    with engine().begin() as c:
        c.execute(delete(atividades).where(atividades.c.contato_id == cid))
        c.execute(delete(contatos).where(contatos.c.id == cid))


# ---------------- Atividades ----------------
COLS_ATV = ["id", "contato_id", "tipo", "texto", "data", "tarefa", "vence", "feita", "feita_em", "usuario_id", "exemplo"]


def listar_atividades(contato_id: int | None = None) -> pd.DataFrame:
    q = select(atividades)
    if contato_id is not None:
        q = q.where(atividades.c.contato_id == contato_id)
    with engine().connect() as c:
        rows = c.execute(q.order_by(atividades.c.data.desc())).mappings().all()
    return pd.DataFrame(rows, columns=COLS_ATV)


def criar_atividade(contato_id: int, tipo: str, texto: str, tarefa: bool = False,
                    vence: date | None = None, usuario_id: int | None = None,
                    data: datetime | None = None, exemplo: bool = False) -> int:
    with engine().begin() as c:
        r = c.execute(insert(atividades).values(
            contato_id=contato_id, tipo=tipo, texto=texto.strip(), data=data or agora(),
            tarefa=tarefa, vence=vence if tarefa else None, feita=False,
            usuario_id=usuario_id, exemplo=exemplo))
        # registrar interação também "mexe" no contato
        c.execute(update(contatos).where(contatos.c.id == contato_id).values(atualizado_em=agora()))
        return r.inserted_primary_key[0]


def marcar_tarefa(aid: int, feita: bool) -> None:
    with engine().begin() as c:
        c.execute(update(atividades).where(atividades.c.id == aid).values(
            feita=feita, feita_em=agora() if feita else None))


def excluir_atividade(aid: int) -> None:
    with engine().begin() as c:
        c.execute(delete(atividades).where(atividades.c.id == aid))


# ---------------- Configuração ----------------
def get_config(chave: str, padrao: str = "") -> str:
    with engine().connect() as c:
        v = c.execute(select(config_tb.c.valor).where(config_tb.c.chave == chave)).scalar_one_or_none()
    return v if v is not None else padrao


def set_config(chave: str, valor: str) -> None:
    with engine().begin() as c:
        existe = c.execute(select(config_tb.c.chave).where(config_tb.c.chave == chave)).first()
        if existe:
            c.execute(update(config_tb).where(config_tb.c.chave == chave).values(valor=valor))
        else:
            c.execute(insert(config_tb).values(chave=chave, valor=valor))


# ---------------- Exemplos ----------------
def contar_exemplos() -> int:
    with engine().connect() as c:
        return c.execute(select(func.count()).select_from(contatos).where(contatos.c.exemplo.is_(True))).scalar_one()


def remover_exemplos() -> None:
    with engine().begin() as c:
        c.execute(delete(atividades).where(atividades.c.exemplo.is_(True)))
        ids = [r[0] for r in c.execute(select(contatos.c.id).where(contatos.c.exemplo.is_(True)))]
        if ids:
            c.execute(delete(atividades).where(atividades.c.contato_id.in_(ids)))
            c.execute(delete(contatos).where(contatos.c.id.in_(ids)))