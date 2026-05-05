"""
Cadastro de chaves PIX por RCA.
Permite importar planilha, editar em massa e salvar no SQLite local.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import streamlit as st

import pix_db
from pix_db import RegistroPix, TIPOS_VALIDOS
from oracle_db import OracleConnection


@st.cache_data(ttl=300, show_spinner=False)
def buscar_rcas_ativos() -> tuple[dict[int, str], str | None]:
    """Retorna ({CODUSUR: NOME}, erro) de todos os RCAs com BLOQUEIO='N'."""
    res: dict[int, str] = {}
    db = OracleConnection()
    if not db.conectar():
        return res, "Falha ao conectar no Oracle"
    erro = None
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT CODUSUR, NVL(NOME,'(sem nome)')
              FROM PCUSUARI
             WHERE NVL(BLOQUEIO,'N') = 'N'
        """)
        for row in cur.fetchall():
            try:
                res[int(row[0])] = str(row[1]).strip()
            except Exception:
                continue
        cur.close()
    except Exception as e:
        erro = f"Erro Oracle: {e}"
    finally:
        db.desconectar()
    return res, erro


@st.cache_data(ttl=300, show_spinner=False)
def buscar_bloqueios(codigos: tuple[int, ...]) -> tuple[dict[int, str], str | None]:
    """Consulta PCUSUARI e retorna ({CODUSUR: 'S'|'N'}, erro). Cache 5 min.

    Faz a consulta em lotes de 200 para não estourar limite de binds do Oracle
    e tenta dois formatos de bind (str e int) já que CODUSUR pode ser NUMBER ou VARCHAR.
    """
    if not codigos:
        return {}, None
    res: dict[int, str] = {}
    db = OracleConnection()
    if not db.conectar():
        return res, "Falha ao conectar no Oracle"
    erro_msg: str | None = None
    try:
        cur = db.get_cursor()
        codigos_unicos = sorted({int(c) for c in codigos})
        CHUNK = 200
        for i in range(0, len(codigos_unicos), CHUNK):
            lote = codigos_unicos[i:i + CHUNK]
            placeholders = ", ".join(f":c{j}" for j in range(len(lote)))
            sql = (f"SELECT CODUSUR, NVL(BLOQUEIO,'N') FROM PCUSUARI "
                   f"WHERE CODUSUR IN ({placeholders})")

            # 1ª tentativa: bind como int
            bind_int = {f"c{j}": v for j, v in enumerate(lote)}
            try:
                cur.execute(sql, bind_int)
                rows = cur.fetchall()
            except Exception:
                rows = []

            # se nada voltou, tenta como string (CODUSUR VARCHAR)
            if not rows:
                bind_str = {f"c{j}": str(v) for j, v in enumerate(lote)}
                try:
                    cur.execute(sql, bind_str)
                    rows = cur.fetchall()
                except Exception as e:
                    erro_msg = f"Erro Oracle: {e}"
                    rows = []

            for row in rows:
                try:
                    res[int(row[0])] = str(row[1]).strip().upper()
                except Exception:
                    continue

        cur.close()
    except Exception as e:
        erro_msg = f"Erro Oracle: {e}"
    finally:
        db.desconectar()
    return res, erro_msg


st.set_page_config(page_title="Cadastro PIX | ROFE", page_icon="💳", layout="wide")

# Reaproveita o CSS principal — versão enxuta (sidebar dark + cards)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }

section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
    background-color:#0f172a !important;
}
section[data-testid="stSidebar"] * { color:#cbd5e1 !important; background-color:transparent !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color:#f8fafc !important; }

/* === Navegação entre páginas (sidebar) === */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    border-radius: 8px !important;
    margin: 2px 6px !important;
    padding: 10px 12px !important;
    font-weight: 500 !important;
    transition: all .15s ease-in-out;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
    background-color: #1e293b !important;
}
/* Página selecionada */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;
    border-left: 4px solid #ef4444 !important;
    box-shadow: 0 2px 8px rgba(37,99,235,.4) !important;
    font-weight: 700 !important;
    padding-left: 14px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #ffffff !important;
    font-weight: 700 !important;
}

.erp-header { background:#0f172a; padding:20px 24px; border-radius:12px; margin-bottom:20px; }
.erp-title  { color:white; font-size:24px; font-weight:700; letter-spacing:1px; }
.erp-title span { color:#ef4444; }
.erp-sub    { color:#94a3b8; font-size:14px; margin-top:4px; }

.card { background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:16px; }

.metric-card { background:#f1f5f9; padding:16px; border-radius:10px; text-align:center; border:1px solid #e2e8f0; }
.metric-card b { display:block; color:#64748b; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; margin-bottom:6px; }
.metric-card .metric-val { font-size:22px; font-weight:700; color:#0f172a; }
.metric-card .metric-val.azul { color:#2563eb; }

div[data-testid="stButton"] > button[kind="primary"] {
    background-color:#2563eb !important; color:white !important; border-radius:8px !important;
    font-weight:700 !important; font-size:15px !important; padding:12px 0 !important; border:none !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="erp-header">
    <div class="erp-title">ROFE <span>|</span></div>
    <div class="erp-sub">Cadastro de Chaves PIX dos RCAs</div>
</div>
""", unsafe_allow_html=True)

# Garante schema
pix_db.init_db()

# ─────────────────────────────────────────────
# Métricas topo
# ─────────────────────────────────────────────
df_atual = pix_db.listar()
total    = len(df_atual)
por_tipo = df_atual["tipo_chave"].value_counts().to_dict() if total else {}

# Status de bloqueio do Oracle (PCUSUARI.BLOQUEIO)
if total:
    bloqueios, erro_oracle = buscar_bloqueios(tuple(int(c) for c in df_atual["codrca"].tolist()))
    df_atual["bloqueado"] = df_atual["codrca"].map(lambda c: bloqueios.get(int(c), "?"))
    if erro_oracle:
        st.warning(f"⚠ Status de bloqueio incompleto — {erro_oracle}")
    nao_localizados = [int(c) for c in df_atual["codrca"] if int(c) not in bloqueios]
    if nao_localizados:
        st.warning(
            f"⚠ {len(nao_localizados)} CODRCA(s) não localizado(s) em PCUSUARI: "
            f"{', '.join(str(c) for c in nao_localizados[:30])}"
            + (" ..." if len(nao_localizados) > 30 else "")
        )
else:
    bloqueios = {}
qtd_bloq = sum(1 for v in bloqueios.values() if v == "S") if bloqueios else 0

# Pré-calcula pendências para o card
_ativos_pre, _ = buscar_rcas_ativos()
_cods_pix_pre = set(int(c) for c in df_atual["codrca"].tolist()) if total else set()
_ign_pre = pix_db.codigos_ignorados()
qtd_pend = sum(1 for c in _ativos_pre if c not in _cods_pix_pre and c not in _ign_pre)

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.markdown(f'<div class="metric-card"><b>RCAs cadastrados</b><div class="metric-val">{total}</div></div>', unsafe_allow_html=True)
m2.markdown(f'<div class="metric-card"><b>CPF/CNPJ</b><div class="metric-val azul">{por_tipo.get("CPF",0)+por_tipo.get("CNPJ",0)}</div></div>', unsafe_allow_html=True)
m3.markdown(f'<div class="metric-card"><b>E-mail</b><div class="metric-val azul">{por_tipo.get("EMAIL",0)}</div></div>', unsafe_allow_html=True)
m4.markdown(f'<div class="metric-card"><b>Tel/Aleatória</b><div class="metric-val azul">{por_tipo.get("TELEFONE",0)+por_tipo.get("ALEATORIA",0)}</div></div>', unsafe_allow_html=True)
m5.markdown(f'<div class="metric-card"><b>Bloqueados</b><div class="metric-val" style="color:#dc2626">{qtd_bloq}</div></div>', unsafe_allow_html=True)
m6.markdown(f'<div class="metric-card"><b>Sem PIX</b><div class="metric-val" style="color:#dc2626">{qtd_pend}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_lista, tab_pend, tab_novo, tab_import = st.tabs(
    ["📋 Cadastro / Edição", "🔔 Sem PIX", "➕ Novo RCA", "📥 Importar Planilha"]
)


# ─────────────────────────────────────────────
# TAB — RCAs ativos sem PIX cadastrado
# ─────────────────────────────────────────────
with tab_pend:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🔔 RCAs ativos (BLOQUEIO = N) sem chave PIX cadastrada")
    st.caption("Lista atualizada via Oracle. Use a opção 'Ignorar' para remover testers / usuários internos da contagem.")

    ativos, erro_at = buscar_rcas_ativos()
    if erro_at:
        st.warning(erro_at)

    cods_pix       = set(int(c) for c in df_atual["codrca"].tolist()) if total else set()
    cods_ignorados = pix_db.codigos_ignorados()

    pendentes = [
        (cod, nome) for cod, nome in ativos.items()
        if cod not in cods_pix and cod not in cods_ignorados
    ]
    pendentes.sort(key=lambda x: x[1])

    pp1, pp2, pp3 = st.columns(3)
    pp1.metric("RCAs ativos", len(ativos))
    pp2.metric("Sem PIX (pendentes)", len(pendentes))
    pp3.metric("Ignorados", len(cods_ignorados))

    if not pendentes:
        st.success("✔ Todos os RCAs ativos têm chave PIX cadastrada (ou estão ignorados).")
    else:
        df_pend = pd.DataFrame(pendentes, columns=["CODRCA", "Nome"])
        st.dataframe(df_pend, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("**🚫 Ignorar um RCA da lista**")
        ig1, ig2, ig3 = st.columns([1, 2, 1])
        ig_cod = ig1.number_input("CODRCA", min_value=0, step=1, value=0, key="ig_cod")
        ig_mot = ig2.text_input("Motivo (ex: tester, vendedor interno)", key="ig_mot")
        if ig3.button("Ignorar", use_container_width=True, disabled=ig_cod == 0):
            pix_db.adicionar_ignorado(int(ig_cod), ig_mot)
            st.success(f"CODRCA {int(ig_cod)} adicionado à lista de ignorados.")
            st.rerun()

    # Lista de ignorados — gerenciar
    df_ign = pix_db.listar_ignorados()
    if not df_ign.empty:
        with st.expander(f"📂 RCAs ignorados ({len(df_ign)})", expanded=False):
            st.dataframe(df_ign, use_container_width=True, hide_index=True)
            rem_cod = st.number_input("Remover CODRCA da lista de ignorados",
                                      min_value=0, step=1, value=0, key="rem_ig")
            if st.button("Remover dos ignorados", disabled=rem_cod == 0, key="btn_rem_ig"):
                pix_db.remover_ignorado(int(rem_cod))
                st.success(f"CODRCA {int(rem_cod)} removido.")
                st.rerun()

    if st.button("🔄 Recarregar do Oracle", key="btn_refresh_pend"):
        buscar_rcas_ativos.clear()
        buscar_bloqueios.clear()
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 1 — Lista editável
# ─────────────────────────────────────────────
with tab_lista:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🔍 Filtros")

    cf1, cf2, cf3 = st.columns([2, 1, 1])
    busca = cf1.text_input("Buscar por código ou nome", "", key="busca_pix")
    tipo_filtro = cf2.selectbox("Tipo de chave", ["Todos"] + list(TIPOS_VALIDOS), key="filtro_tipo")
    bloq_filtro = cf3.selectbox("Bloqueio", ["Todos", "Bloqueados (S)", "Liberados (N)"], key="filtro_bloq")

    df_view = df_atual.copy()
    if "bloqueado" not in df_view.columns:
        df_view["bloqueado"] = "?"
    if busca.strip():
        b = busca.strip().lower()
        df_view = df_view[
            df_view["codrca"].astype(str).str.contains(b, na=False) |
            df_view["nome_rca"].str.lower().str.contains(b, na=False)
        ]
    if tipo_filtro != "Todos":
        df_view = df_view[df_view["tipo_chave"] == tipo_filtro]
    if bloq_filtro == "Bloqueados (S)":
        df_view = df_view[df_view["bloqueado"] == "S"]
    elif bloq_filtro == "Liberados (N)":
        df_view = df_view[df_view["bloqueado"] == "N"]

    st.markdown(f"**{len(df_view)} registro(s)**")
    if st.button("🔄 Atualizar status de bloqueio (Oracle)", key="btn_refresh_bloq"):
        buscar_bloqueios.clear()
        st.rerun()

    if df_view.empty:
        st.info("Nenhum registro. Use as outras abas para cadastrar ou importar.")
    else:
        edited = st.data_editor(
            df_view[["codrca", "nome_rca", "chave_pix", "tipo_chave", "bloqueado", "dt_atualizacao"]],
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=["codrca", "bloqueado", "dt_atualizacao"],
            column_config={
                "codrca":         st.column_config.NumberColumn("CODRCA", width="small"),
                "nome_rca":       st.column_config.TextColumn("Nome RCA"),
                "chave_pix":      st.column_config.TextColumn("Chave PIX"),
                "tipo_chave":     st.column_config.SelectboxColumn("Tipo", options=list(TIPOS_VALIDOS), width="small"),
                "bloqueado":      st.column_config.TextColumn("Bloq.", width="small", help="PCUSUARI.BLOQUEIO (S=bloqueado, N=liberado, ?=não localizado)"),
                "dt_atualizacao": st.column_config.TextColumn("Atualizado em", width="medium"),
            },
            key="editor_pix",
        )

        c_save, c_del = st.columns([1, 1])
        if c_save.button("💾 Salvar alterações", type="primary", use_container_width=True):
            # Compara linha a linha contra df_view original
            orig = df_view.set_index("codrca")
            mod  = edited.set_index("codrca")
            alterados: list[RegistroPix] = []
            for cod in mod.index:
                if cod in orig.index:
                    o, m = orig.loc[cod], mod.loc[cod]
                    if (o["nome_rca"] != m["nome_rca"]
                        or o["chave_pix"] != m["chave_pix"]
                        or o["tipo_chave"] != m["tipo_chave"]):
                        alterados.append(RegistroPix(
                            codrca=int(cod),
                            nome_rca=str(m["nome_rca"]),
                            chave_pix=str(m["chave_pix"]),
                            tipo_chave=str(m["tipo_chave"]),
                        ))
            if not alterados:
                st.info("Nenhuma alteração detectada.")
            else:
                ok, erros = pix_db.upsert_lote(alterados)
                if ok:
                    st.success(f"{ok} registro(s) atualizado(s).")
                if erros:
                    st.error("Erros:\n" + "\n".join(f"• {e}" for e in erros))
                st.rerun()

        with c_del:
            cod_del = st.number_input("Excluir CODRCA", min_value=0, step=1, value=0, key="cod_del")
            if st.button("🗑 Excluir", use_container_width=True, disabled=cod_del == 0):
                pix_db.remover(int(cod_del))
                st.success(f"CODRCA {cod_del} removido.")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 2 — Novo cadastro
# ─────────────────────────────────────────────
with tab_novo:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Cadastrar novo RCA")

    with st.form("form_novo_pix", clear_on_submit=False):
        f1, f2 = st.columns(2)
        n_cod  = f1.number_input("CODRCA *", min_value=1, step=1, value=1, key="form_cod")
        n_tipo = f2.selectbox("Tipo de chave *", list(TIPOS_VALIDOS), key="form_tipo")
        n_nome = st.text_input("Nome do RCA *", key="form_nome")
        n_pix  = st.text_input("Chave PIX *",   key="form_pix")
        salvar = st.form_submit_button("💾 Cadastrar", type="primary", use_container_width=True)

        if salvar:
            existente = pix_db.buscar(int(n_cod))
            novo_reg  = RegistroPix(codrca=int(n_cod), nome_rca=n_nome,
                                    chave_pix=n_pix, tipo_chave=n_tipo)
            err_val = pix_db.validar(novo_reg)
            if err_val:
                st.error(err_val)
            elif existente:
                st.session_state["pix_form_conflito"] = {
                    "atual": existente.__dict__, "novo": novo_reg.__dict__,
                }
            else:
                try:
                    pix_db.upsert(novo_reg)
                    st.success(f"CODRCA {n_cod} cadastrado.")
                    st.session_state.pop("pix_form_conflito", None)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    # Caixa de confirmação quando o RCA já existe
    conflito = st.session_state.get("pix_form_conflito")
    if conflito:
        st.warning(f"⚠ CODRCA **{conflito['atual']['codrca']}** já está cadastrado.")
        cmp = pd.DataFrame([
            {"Campo": "Nome",       "Atual": conflito["atual"]["nome_rca"],   "Novo": conflito["novo"]["nome_rca"]},
            {"Campo": "Chave PIX",  "Atual": conflito["atual"]["chave_pix"],  "Novo": conflito["novo"]["chave_pix"]},
            {"Campo": "Tipo Chave", "Atual": conflito["atual"]["tipo_chave"], "Novo": conflito["novo"]["tipo_chave"]},
        ])
        st.dataframe(cmp, use_container_width=True, hide_index=True)

        cb1, cb2 = st.columns(2)
        if cb1.button("✔ Atualizar mesmo assim", type="primary", use_container_width=True, key="conf_upd"):
            try:
                pix_db.upsert(RegistroPix(**conflito["novo"]))
                st.success(f"CODRCA {conflito['atual']['codrca']} atualizado.")
                st.session_state.pop("pix_form_conflito", None)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if cb2.button("✘ Cancelar", use_container_width=True, key="conf_can"):
            st.session_state.pop("pix_form_conflito", None)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 3 — Importar planilha
# ─────────────────────────────────────────────
with tab_import:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Importar planilha de chaves PIX")
    st.caption("Colunas esperadas: **CODRCA**, **RCA** (nome), **pix** (chave), **tipo_chave**. "
               "Aceita variações de nome (codigo, nome, chave, tipo, etc.).")

    up = st.file_uploader("Selecione o arquivo .xlsx", type=["xlsx"], key="upl_pix")

    def _ler_excel_auto(uploaded) -> pd.DataFrame | None:
        """Lê o Excel localizando automaticamente a linha do cabeçalho."""
        alvos = {"codrca", "rca", "pix", "tipo_chave", "tipo", "chave", "chave_pix"}
        bruto = pd.read_excel(uploaded, header=None)
        for i in range(min(10, len(bruto))):
            linha = [str(v).strip().lower() for v in bruto.iloc[i].tolist()]
            if sum(1 for v in linha if v in alvos) >= 2:
                uploaded.seek(0)
                return pd.read_excel(uploaded, header=i)
        uploaded.seek(0)
        return pd.read_excel(uploaded)

    if up:
        try:
            df_in = _ler_excel_auto(up)
        except Exception as e:
            st.error(f"Falha ao ler o Excel: {e}")
            df_in = None

        if df_in is not None and not df_in.empty:
            st.markdown(f"**Linhas lidas:** {len(df_in)}")
            st.dataframe(df_in.head(20), use_container_width=True, hide_index=True)

            regs, avisos = pix_db.df_para_registros(df_in)
            for w in avisos:
                st.warning(w)

            if regs:
                # Classifica: novos / a atualizar / inválidos
                existentes_cods = set(df_atual["codrca"].tolist()) if not df_atual.empty else set()
                novos, atualizar, invalidos = [], [], []
                for r in regs:
                    err = pix_db.validar(r)
                    if err:
                        invalidos.append((r, err))
                    elif r.codrca in existentes_cods:
                        atualizar.append(r)
                    else:
                        novos.append(r)

                cN, cA, cI = st.columns(3)
                cN.metric("🆕 Novos",          len(novos))
                cA.metric("♻ A atualizar",     len(atualizar))
                cI.metric("❌ Inválidos",      len(invalidos))

                with st.expander(f"🆕 Novos ({len(novos)})", expanded=False):
                    if novos:
                        st.dataframe(pd.DataFrame([{
                            "CODRCA": r.codrca, "Nome": r.nome_rca,
                            "Chave": r.chave_pix, "Tipo": r.tipo_chave,
                        } for r in novos]), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Nenhum.")

                with st.expander(f"♻ Já cadastrados — comparação ({len(atualizar)})", expanded=False):
                    if atualizar:
                        cmp_rows = []
                        for r in atualizar:
                            atual = pix_db.buscar(r.codrca)
                            mudou = (atual.nome_rca != r.nome_rca
                                     or atual.chave_pix != r.chave_pix
                                     or atual.tipo_chave != r.tipo_chave)
                            cmp_rows.append({
                                "CODRCA":      r.codrca,
                                "Nome atual":  atual.nome_rca,
                                "Nome novo":   r.nome_rca,
                                "Chave atual": atual.chave_pix,
                                "Chave nova":  r.chave_pix,
                                "Tipo atual":  atual.tipo_chave,
                                "Tipo novo":   r.tipo_chave,
                                "Mudou?":      "SIM" if mudou else "não",
                            })
                        st.dataframe(pd.DataFrame(cmp_rows),
                                     use_container_width=True, hide_index=True)
                    else:
                        st.caption("Nenhum.")

                with st.expander(f"❌ Inválidos ({len(invalidos)})", expanded=False):
                    if invalidos:
                        st.dataframe(pd.DataFrame([{
                            "CODRCA": r.codrca, "Nome": r.nome_rca,
                            "Chave": r.chave_pix, "Tipo": r.tipo_chave,
                            "Motivo": err,
                        } for r, err in invalidos]),
                            use_container_width=True, hide_index=True)
                    else:
                        st.caption("Nenhum.")

                st.markdown("---")
                atualizar_existentes = st.checkbox(
                    "Sobrescrever os RCAs já cadastrados",
                    value=False,
                    help="Se desmarcado, somente registros NOVOS serão importados. "
                         "Os já cadastrados serão ignorados."
                )

                qtd_novos = len(novos)
                qtd_upd   = len(atualizar) if atualizar_existentes else 0
                total_op  = qtd_novos + qtd_upd

                if st.button(
                    f"📥 Importar — {qtd_novos} novo(s)" + (f" + {qtd_upd} atualização(ões)" if qtd_upd else ""),
                    type="primary", use_container_width=True, disabled=total_op == 0
                ):
                    a_gravar = list(novos) + (list(atualizar) if atualizar_existentes else [])
                    ignorados = [] if atualizar_existentes else list(atualizar)
                    ok, erros_grav = pix_db.upsert_lote(a_gravar)

                    st.session_state["pix_import_result"] = {
                        "ok":        ok,
                        "novos":     len(novos),
                        "atualizados": qtd_upd,
                        "ignorados": [
                            {"CODRCA": r.codrca, "Nome": r.nome_rca,
                             "Chave": r.chave_pix, "Tipo": r.tipo_chave,
                             "Motivo": "Já cadastrado — sobrescrita não autorizada"}
                            for r in ignorados
                        ],
                        "invalidos": [
                            {"CODRCA": r.codrca, "Nome": r.nome_rca,
                             "Chave": r.chave_pix, "Tipo": r.tipo_chave,
                             "Motivo": err}
                            for r, err in invalidos
                        ],
                        "erros_grav": erros_grav,
                    }

    # Resultado persistente da última importação
    res = st.session_state.get("pix_import_result")
    if res:
        st.markdown("---")
        st.markdown("#### 📊 Resultado da última importação")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✔ Gravados",       res["ok"])
        c2.metric("🆕 Novos",          res.get("novos", 0))
        c3.metric("♻ Atualizados",     res.get("atualizados", 0))
        c4.metric("⏭ Ignorados",       len(res.get("ignorados", [])))

        if res.get("ignorados"):
            st.markdown("**⏭ Ignorados (já cadastrados — sobrescrita não autorizada):**")
            st.dataframe(pd.DataFrame(res["ignorados"]),
                         use_container_width=True, hide_index=True)

        if res["invalidos"]:
            st.markdown("**❌ Inválidos (falha de validação):**")
            st.dataframe(pd.DataFrame(res["invalidos"]),
                         use_container_width=True, hide_index=True)

        if res["erros_grav"]:
            st.markdown("**⚠ Erros durante a gravação:**")
            for e in res["erros_grav"]:
                st.error(f"• {e}")

        if st.button("Limpar resultado", key="btn_clear_res"):
            st.session_state.pop("pix_import_result", None)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
