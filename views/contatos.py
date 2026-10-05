import io

import pandas as pd
import streamlit as st

from crm import db
from crm.config import ETAPA_IDS, ETAPA_NOME, ORIGENS, data_br, hoje
from crm.ui import ficha_contato, filtrar_meus, nomes_usuarios, proximas_tarefas

aberto = st.session_state.get("contato_aberto")
if aberto:
    ficha_contato(int(aberto))
    st.stop()

st.title("Contatos")

df = filtrar_meus(db.listar_contatos())
if df.empty:
    st.info("Nenhum contato cadastrado ainda. Use **➕ Novo contato** na barra lateral.")
    st.stop()

usuarios = nomes_usuarios()
f1, f2, f3 = st.columns([3, 2, 2])
busca = f1.text_input("Buscar", placeholder="Nome, empresa, e-mail ou telefone")
etapas = f2.multiselect("Etapas", ETAPA_IDS, format_func=ETAPA_NOME.get)
origens = f3.multiselect("Origem", ORIGENS)

if busca:
    b = busca.lower()
    alvo = (df["nome"] + " " + df["empresa"].fillna("") + " " + df["email"].fillna("") + " " + df["telefone"].fillna("")).str.lower()
    df = df[alvo.str.contains(b, regex=False)]
if etapas:
    df = df[df["etapa"].isin(etapas)]
if origens:
    df = df[df["origem"].isin(origens)]

prox = proximas_tarefas(db.listar_atividades())
tab = df.merge(prox, left_on="id", right_on="contato_id", how="left")
tabela = pd.DataFrame({
    "Nome": tab["nome"] + tab["exemplo"].map({True: " (exemplo)", False: ""}),
    "Empresa": tab["empresa"],
    "Etapa": tab["etapa"].map(ETAPA_NOME),
    "Valor (R$)": tab["valor"],
    "Próxima tarefa": pd.to_datetime(tab["vence"]),
    "Responsável": tab["responsavel_id"].map(usuarios),
    "Origem": tab["origem"],
    "Telefone": tab["telefone"],
})

st.caption(f"{len(tabela)} contato(s). Selecione uma linha para abrir a ficha.")
sel = st.dataframe(
    tabela, hide_index=True, on_select="rerun", selection_mode="single-row", key="tabela_contatos",
    column_config={
        "Valor (R$)": st.column_config.NumberColumn(format="R$ %.0f"),
        "Próxima tarefa": st.column_config.DateColumn(format="DD/MM/YYYY"),
    },
)
linhas = sel.selection.rows if sel else []
if linhas:
    st.session_state["contato_aberto"] = int(tab.iloc[linhas[0]]["id"])
    st.session_state.pop("tabela_contatos", None)
    st.rerun()

# ---- Exportação ----
exp = tabela.copy()
exp["Próxima tarefa"] = exp["Próxima tarefa"].dt.strftime("%d/%m/%Y")
exp["E-mail"] = tab["email"]
exp["Cadastro"] = tab["criado_em"].map(data_br)
exp["Notas"] = tab["notas"]
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    exp.to_excel(w, index=False, sheet_name="Contatos")
c1, c2, _ = st.columns([1, 1, 3])
c1.download_button("⬇️ Excel", buf.getvalue(), file_name=f"contatos-{hoje():%Y-%m-%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
c2.download_button("⬇️ CSV", exp.to_csv(index=False, sep=";").encode("utf-8-sig"),
                   file_name=f"contatos-{hoje():%Y-%m-%d}.csv", mime="text/csv", width="stretch")
