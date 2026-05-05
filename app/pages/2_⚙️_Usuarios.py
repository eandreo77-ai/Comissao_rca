"""
Página de administração de usuários (só perfil admin).
CRUD da tabela `usuarios` no MariaDB.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd

import auth
import db
from styles import aplicar_visual, header

# ── Login obrigatório ──────────────────────────────────────────────────────
auth.gate_login()
aplicar_visual()
header(
    titulo="Usuários",
    subtitulo="Cadastro de emails autorizados a acessar o sistema",
    icone="⚙️",
    usuario=auth.usuario_logado()["email"],
)

# ── Só admin ───────────────────────────────────────────────────────────────
if not auth.is_admin():
    st.error("Acesso restrito a administradores.")
    st.stop()


# ── Lista usuários atuais ──────────────────────────────────────────────────
st.markdown("#### Usuários cadastrados")

df = pd.DataFrame(
    db.fetch_all(
        """
        SELECT id, username, email, nome, perfil, ativo,
               DATE_FORMAT(criado_em, '%d/%m/%Y %H:%i') AS criado_em,
               DATE_FORMAT(ultimo_login, '%d/%m/%Y %H:%i') AS ultimo_login
          FROM usuarios
         ORDER BY criado_em DESC
        """
    )
)
if df.empty:
    st.info("Nenhum usuário cadastrado.")
else:
    df_display = df.copy()
    df_display["Ativo"] = df_display["ativo"].map({1: "✓", 0: "✗"})
    df_display = df_display[
        ["id", "username", "email", "nome", "perfil", "Ativo", "criado_em", "ultimo_login"]
    ]
    df_display.columns = [
        "ID", "Usuário", "Email", "Nome", "Perfil", "Ativo", "Criado em", "Último login"
    ]
    st.dataframe(df_display, use_container_width=True, hide_index=True)


# ── Form: adicionar novo usuário ───────────────────────────────────────────
st.markdown("#### Adicionar usuário")
with st.form("novo_user", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    novo_username = col_a.text_input("Username (curto, sem espaço) *")
    novo_email = col_b.text_input("Email * (corporativo)")
    novo_nome = st.text_input("Nome completo *")
    novo_perfil = st.selectbox("Perfil", ["operador", "admin"], index=0)

    if st.form_submit_button("Adicionar", type="primary"):
        if not novo_username or not novo_email or not novo_nome:
            st.error("Preencha username, email e nome.")
        elif "@" not in novo_email:
            st.error("Email inválido.")
        else:
            try:
                db.execute(
                    """
                    INSERT INTO usuarios (username, email, nome, perfil, ativo)
                    VALUES (%s, %s, %s, %s, 1)
                    """,
                    (novo_username.strip(), novo_email.strip().lower(),
                     novo_nome.strip(), novo_perfil),
                )
                st.success(f"Usuário '{novo_username}' adicionado.")
                st.rerun()
            except Exception as e:
                err_msg = str(e).lower()
                if "duplicate" in err_msg or "unique" in err_msg:
                    st.error("Já existe um usuário com este username ou email.")
                else:
                    st.error(f"Erro ao gravar: {e}")


# ── Ativar/desativar usuário ───────────────────────────────────────────────
if not df.empty:
    st.markdown("#### Ativar / desativar")
    col_x, col_y = st.columns([3, 1])
    user_sel = col_x.selectbox(
        "Selecione o usuário",
        df["id"].tolist(),
        format_func=lambda i: (
            f"#{i} — {df.loc[df['id']==i, 'email'].iloc[0]} "
            f"({'ativo' if df.loc[df['id']==i, 'ativo'].iloc[0] else 'inativo'})"
        ),
    )
    user_atual = df.loc[df["id"] == user_sel].iloc[0]

    if user_atual["ativo"]:
        if col_y.button("Desativar", use_container_width=True):
            if user_atual["id"] == auth.usuario_logado()["id"]:
                st.error("Você não pode se desativar.")
            else:
                db.execute("UPDATE usuarios SET ativo = 0 WHERE id = %s", (int(user_sel),))
                st.success("Usuário desativado.")
                st.rerun()
    else:
        if col_y.button("Reativar", use_container_width=True, type="primary"):
            db.execute("UPDATE usuarios SET ativo = 1 WHERE id = %s", (int(user_sel),))
            st.success("Usuário reativado.")
            st.rerun()
