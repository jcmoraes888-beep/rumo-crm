# Rumo CRM

CRM para pequenos negócios feito em Python + Streamlit: contatos, funil de vendas, histórico de interações, tarefas e painel de resultados.

## Funcionalidades

- **Login com usuários**: o primeiro acesso cria o administrador. O administrador cadastra vendedores em Ajustes.
- **Painel**: oportunidades abertas, valor em negociação, fechado no mês, taxa de conversão, ticket médio, funil por etapa e origem dos contatos.
- **Funil**: quadro por etapa (Novo lead → Contato feito → Proposta → Negociação → Ganho/Perdido) com botões para avançar e voltar.
- **Contatos**: busca, filtros, ficha completa com botão de WhatsApp, histórico e exportação em Excel e CSV.
- **Tarefas**: atrasadas, de hoje e próximas, com marcação de concluída.
- **Ajustes**: nome da empresa (white label), usuários, visibilidade por vendedor e dados de exemplo.

## Rodar no computador

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Sem configuração, os dados ficam no arquivo `rumo_crm.db` (SQLite), na pasta do projeto.

## Publicar no Streamlit Community Cloud

1. Suba a pasta para um repositório no GitHub.
2. Crie um banco PostgreSQL gratuito no [Neon](https://neon.tech) ou no [Supabase](https://supabase.com) e copie a connection string.
3. No Streamlit Cloud, em **New app**, escolha o repositório e o arquivo `app.py`.
4. Em **Advanced settings → Secrets**, cole:
   ```toml
   DATABASE_URL = "postgresql://usuario:senha@host:5432/banco?sslmode=require"
   ```
5. Abra o app e crie o administrador.

> O Streamlit Cloud apaga arquivos locais quando o app reinicia. Por isso, em produção use sempre o PostgreSQL. O SQLite serve só para testes.

## Um CRM por cliente

Cada cliente recebe seu próprio deploy e seu próprio banco: o mesmo repositório com um `DATABASE_URL` diferente. Os dados de um cliente nunca se misturam com os de outro, e o nome da empresa é configurado em Ajustes.

## Estrutura

```
app.py              navegação, login e barra lateral
crm/config.py       etapas, origens, tipos de interação e formatação
crm/db.py           banco de dados (SQLAlchemy: SQLite ou PostgreSQL)
crm/auth.py         login e senhas (PBKDF2)
crm/ui.py           ficha do contato, formulário e componentes
crm/seed.py         dados de exemplo fictícios
views/              páginas: painel, funil, contatos, tarefas, ajustes
```
