"""
Histórico de importações.
- Admin: vê todas as importações
- Operador: vê só as suas
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd

import auth
import audit
from styles import aplicar_visual, header

# ── Login obrigatório ──────────────────────────────────────────────────────
auth.gate_login()
aplicar_visual()
header(
    titulo="Histórico de Importações",
    subtitulo="Auditoria das gravações realizadas",
    icone="📊",
    usuario=auth.usuario_logado()["email"],
)

usuario = auth.usuario_logado()
admin   = auth.is_admin()

# ── Listagem cabeçalhos ────────────────────────────────────────────────────
filtro_id = None if admin else usuario["id"]
imps = audit.listar_historico(usuario_id=filtro_id, limit=200)

if not imps:
    st.info("Nenhuma importação encontrada ainda.")
    st.stop()

# Resumo
total_imps   = len(imps)
total_grav   = sum(1 for i in imps if i["status"] == "gravado")
total_erro   = sum(1 for i in imps if i["status"] == "erro")
valor_total  = sum(float(i["valor_total"] or 0) for i in imps if i["status"] == "gravado")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Importações",     total_imps)
c2.metric("Gravadas",        total_grav)
c3.metric("Com erro",        total_erro)
c4.metric("Valor total (R$)", f"{valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# Tabela
df = pd.DataFrame(imps)
df_show = df.copy()
df_show["valor_total"]  = df_show["valor_total"].apply(
    lambda v: f"R$ {float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)
df_show["iniciada_em"]   = pd.to_datetime(df_show["iniciada_em"]).dt.strftime("%d/%m/%Y %H:%M")
df_show["finalizada_em"] = pd.to_datetime(df_show["finalizada_em"]).dt.strftime("%d/%m/%Y %H:%M").fillna("-")

if admin:
    df_show = df_show[
        ["id", "usuario_email", "arquivo_nome", "total_itens", "valor_total",
         "status", "iniciada_em", "finalizada_em"]
    ]
    df_show.columns = ["ID", "Usuário", "Arquivo", "Itens", "Valor",
                       "Status", "Iniciada em", "Finalizada em"]
else:
    df_show = df_show[
        ["id", "arquivo_nome", "total_itens", "valor_total",
         "status", "iniciada_em", "finalizada_em"]
    ]
    df_show.columns = ["ID", "Arquivo", "Itens", "Valor",
                       "Status", "Iniciada em", "Finalizada em"]

st.dataframe(df_show, use_container_width=True, hide_index=True)


# ── Detalhe de uma importação ──────────────────────────────────────────────
st.markdown("---")
st.markdown("#### Detalhe da importação")

ids = df["id"].tolist()
imp_sel = st.selectbox(
    "Selecione uma importação",
    ids,
    format_func=lambda i: f"#{i} — {df.loc[df['id']==i, 'arquivo_nome'].iloc[0]} "
                         f"({df.loc[df['id']==i, 'iniciada_em'].iloc[0]})",
)
if imp_sel:
    imp_info = df.loc[df["id"] == imp_sel].iloc[0]
    if imp_info["status"] == "erro" and imp_info["erro_msg"]:
        st.error(f"Erro: {imp_info['erro_msg']}")

    itens = audit.listar_itens(int(imp_sel))
    if not itens:
        st.info("Sem itens registrados.")
    else:
        df_itens = pd.DataFrame(itens)
        df_itens["valor"] = df_itens["valor"].apply(
            lambda v: f"R$ {float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_itens["dtvenc"] = pd.to_datetime(df_itens["dtvenc"]).dt.strftime("%d/%m/%Y")
        # CODUSUR como string sem separador de milhar
        df_itens["codusur"] = df_itens["codusur"].apply(
            lambda v: str(int(v)) if pd.notna(v) else "-"
        )
        # RECNUM como string sem separador de milhar (pra busca no WinThor)
        df_itens["recnum_oracle"] = df_itens["recnum_oracle"].apply(
            lambda v: str(int(v)) if pd.notna(v) else "-"
        )
        # Erro: troca "None"/NaN por string vazia (mais limpo na UI)
        df_itens["erro_msg"] = df_itens["erro_msg"].apply(
            lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
        )
        df_itens = df_itens[
            ["id", "codusur", "nome_rca", "valor", "dtvenc",
             "recnum_oracle", "status", "erro_msg"]
        ]
        df_itens.columns = [
            "ID", "CODUSUR", "Nome RCA", "Valor", "DTVENC",
            "RECNUM Oracle", "Status", "Erro",
        ]
        st.dataframe(df_itens, use_container_width=True, hide_index=True)
