"""
Padrão visual ROFE — CSS custom + componentes para alinhar o app de
Comissão RCA ao layout do rofe.app/contabilidade/.

Como usar (no topo do app.py e de cada página em pages/):
    from styles import aplicar_visual, header, secao
    aplicar_visual()
    header("Importação de Comissão RCA",
           subtitulo="Lançamento no contas a pagar (rotina 749)",
           usuario="admin")

    with secao("Parâmetros", icone="⚙️"):
        # ... inputs aqui ...
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Optional

import streamlit as st


# =============================================================================
# Paleta ROFE — exposta como variáveis CSS pra fácil ajuste
# =============================================================================
_CORES = {
    "navy":        "#1e3a6b",   # header institucional
    "navy_dark":   "#15294b",   # hover do header
    "blue":        "#2563eb",   # ações primárias
    "blue_light":  "#eff6ff",   # background do upload
    "blue_border": "#bfdbfe",   # borda tracejada do upload
    "green":       "#16a34a",   # sucesso
    "red":         "#dc2626",   # erro
    "yellow":      "#f59e0b",   # alerta
    "bg":          "#f3f4f6",   # fundo da página
    "card_bg":     "#ffffff",   # cards
    "border":      "#e5e7eb",   # bordas suaves
    "text":        "#111827",   # texto principal
    "text_muted":  "#6b7280",   # texto auxiliar
    "text_label":  "#374151",   # labels
}


# =============================================================================
# CSS GLOBAL
# =============================================================================
def _build_css() -> str:
    """Retorna o CSS completo, com cores interpoladas."""
    c = _CORES
    return f"""
    /* ── Fonte Inter via Google Fonts (com fallback pra system fonts) ────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Force fonte stack moderna em TUDO, com fallback robusto pra
       quando Google Fonts estiver bloqueado/lento. */
    *, *::before, *::after {{
        font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont,
                     'Helvetica Neue', Arial, sans-serif !important;
    }}

    :root {{
        --rofe-navy:        {c["navy"]};
        --rofe-navy-dark:   {c["navy_dark"]};
        --rofe-blue:        {c["blue"]};
        --rofe-blue-light:  {c["blue_light"]};
        --rofe-blue-border: {c["blue_border"]};
        --rofe-green:       {c["green"]};
        --rofe-red:         {c["red"]};
        --rofe-yellow:      {c["yellow"]};
        --rofe-bg:          {c["bg"]};
        --rofe-card-bg:     {c["card_bg"]};
        --rofe-border:      {c["border"]};
        --rofe-text:        {c["text"]};
        --rofe-text-muted:  {c["text_muted"]};
        --rofe-text-label:  {c["text_label"]};
    }}

    /* ── Tipografia global ────────────────────────────────────────────────── */
    html, body, [class*="css"], .stApp, .stMarkdown {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: var(--rofe-text);
    }}

    /* ── Esconde header nativo do Streamlit (usamos o nosso) ──────────────── */
    [data-testid="stHeader"] {{
        display: none;
    }}

    /* ── Esconde menu hamburguer e badge "Made with Streamlit" ────────────── */
    #MainMenu, footer, [data-testid="stStatusWidget"] {{
        visibility: hidden;
    }}

    /* ── Reduz padding do container principal pra header colar no topo ────── */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }}

    /* ── HEADER ROFE (navy fixo no topo) ──────────────────────────────────── */
    .rofe-header {{
        background: var(--rofe-navy);
        color: white;
        padding: 14px 28px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: -1rem -1rem 1.5rem -1rem;
        border-radius: 0;
        font-size: 14px;
    }}
    .rofe-header-left {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .rofe-logo {{
        font-weight: 700;
        font-size: 20px;
        letter-spacing: 0.5px;
    }}
    .rofe-divider {{
        color: rgba(255,255,255,0.4);
        font-weight: 300;
    }}
    .rofe-app-name {{
        font-weight: 400;
        font-size: 14px;
        opacity: 0.9;
    }}
    .rofe-header-right {{
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    .rofe-user {{
        font-size: 13px;
        opacity: 0.95;
    }}
    .rofe-logout {{
        color: white;
        background: transparent;
        border: 1px solid rgba(255,255,255,0.5);
        padding: 5px 14px;
        border-radius: 4px;
        text-decoration: none;
        font-size: 13px;
        transition: background 0.15s;
    }}
    .rofe-logout:hover {{
        background: rgba(255,255,255,0.12);
        color: white;
    }}

    /* ── Título da página + subtítulo ─────────────────────────────────────── */
    .rofe-page-title {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
    }}
    .rofe-page-title .rofe-icon {{
        font-size: 28px;
    }}
    .rofe-page-title h1 {{
        font-size: 26px;
        font-weight: 600;
        margin: 0;
        color: var(--rofe-text);
    }}
    .rofe-page-subtitle {{
        color: var(--rofe-text-muted);
        font-size: 13px;
        margin: 0 0 24px 38px;
    }}

    /* ── Card de seção (parâmetros, upload, resultados) ───────────────────── */
    .rofe-section-title {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 600;
        font-size: 15px;
        color: var(--rofe-text);
        margin: 8px 0 14px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--rofe-border);
    }}
    .rofe-section-title .icon {{
        color: var(--rofe-blue);
        font-size: 18px;
    }}

    /* ── Cards informativos (4 colunas com valor grande) ──────────────────── */
    .rofe-info-card {{
        background: var(--rofe-card-bg);
        border: 1px solid var(--rofe-border);
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .rofe-info-card-label {{
        text-transform: uppercase;
        font-size: 11px;
        font-weight: 500;
        color: var(--rofe-text-muted);
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }}
    .rofe-info-card-value {{
        font-size: 20px;
        font-weight: 600;
        color: var(--rofe-text);
    }}

    /* ── Stylistic tweaks nos componentes Streamlit ───────────────────────── */
    /* Inputs com borda mais clean */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div {{
        border-radius: 6px !important;
        border: 1px solid var(--rofe-border) !important;
    }}
    .stTextInput > label,
    .stNumberInput > label,
    .stDateInput > label,
    .stSelectbox > label,
    .stFileUploader > label {{
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--rofe-text-label) !important;
    }}

    /* Botão primário azul forte */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {{
        background: var(--rofe-blue) !important;
        border: 1px solid var(--rofe-blue) !important;
        color: white !important;
        border-radius: 6px !important;
        padding: 8px 18px !important;
        font-weight: 500 !important;
        transition: background 0.15s;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
    }}
    /* Botão secundário (outline) */
    .stButton > button[kind="secondary"] {{
        background: white !important;
        border: 1px solid var(--rofe-border) !important;
        color: var(--rofe-text) !important;
        border-radius: 6px !important;
    }}

    /* st.success / st.error / st.warning com bordas suaves */
    [data-testid="stAlert"] {{
        border-radius: 6px;
        border-left-width: 4px;
    }}

    /* File uploader: área tracejada azul claro (alinha com /contabilidade/) */
    [data-testid="stFileUploaderDropzone"] {{
        background: var(--rofe-blue-light) !important;
        border: 2px dashed var(--rofe-blue-border) !important;
        border-radius: 8px !important;
        padding: 32px !important;
    }}

    /* Tabela: linhas zebradas, header navy claro */
    [data-testid="stDataFrame"] table {{
        font-size: 13px !important;
    }}
    [data-testid="stDataFrame"] thead th {{
        background: #1e3a6b !important;
        color: white !important;
        font-weight: 600 !important;
    }}

    /* Métricas (st.metric) com card branco */
    [data-testid="stMetric"] {{
        background: var(--rofe-card-bg);
        border: 1px solid var(--rofe-border);
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    [data-testid="stMetricLabel"] {{
        color: var(--rofe-text-muted) !important;
        text-transform: uppercase;
        font-size: 11px !important;
        letter-spacing: 0.5px;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--rofe-text) !important;
        font-size: 20px !important;
        font-weight: 600 !important;
    }}

    /* ── Classes legacy do app.py original (.metric-card, .metric-val) ─── */
    /* Reproduzidas em LIGHT pra alinhar com o tema novo */
    .metric-card {{
        background: var(--rofe-card-bg);
        border: 1px solid var(--rofe-border);
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        margin-bottom: 8px;
    }}
    .metric-card b {{
        display: block;
        text-transform: uppercase;
        font-size: 11px;
        font-weight: 500;
        color: var(--rofe-text-muted);
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }}
    .metric-val {{
        font-size: 22px;
        font-weight: 600;
        color: var(--rofe-text);
        line-height: 1.2;
    }}
    .metric-val.azul     {{ color: var(--rofe-blue); }}
    .metric-val.verde    {{ color: var(--rofe-green); }}
    .metric-val.vermelho {{ color: var(--rofe-red); }}
    .metric-val.amarelo  {{ color: var(--rofe-yellow); }}

    /* Esconde a banner ANTIGA .erp-header (caso ainda esteja sendo
       chamada). O header novo vem do componente header() do styles.py. */
    .erp-header, .erp-banner, .erp-title, .erp-sub {{
        display: none !important;
    }}

    /* Sidebar do Streamlit em tema claro */
    section[data-testid="stSidebar"] {{
        background: #f9fafb !important;
        border-right: 1px solid var(--rofe-border);
    }}
    section[data-testid="stSidebar"] * {{
        color: var(--rofe-text) !important;
    }}
    """


# =============================================================================
# API PÚBLICA
# =============================================================================
def aplicar_visual(
    page_title: str = "Comissão RCA — ROFE",
    page_icon: str = "💰",
    layout: str = "wide",
) -> None:
    """Configura o tema visual do app.

    Chame UMA VEZ no topo de app.py e de cada arquivo em pages/.
    Idempotente: chamadas repetidas são seguras (ex: page reload).
    """
    # set_page_config tem que ser a 1ª chamada Streamlit. Tenta — se já foi
    # chamado antes (caso comum), ignora silenciosamente.
    try:
        st.set_page_config(
            page_title=page_title,
            page_icon=page_icon,
            layout=layout,
            initial_sidebar_state="expanded",
        )
    except Exception:
        pass

    # CSS injection
    st.markdown(f"<style>{_build_css()}</style>", unsafe_allow_html=True)


def header(
    titulo: str,
    subtitulo: Optional[str] = None,
    usuario: Optional[str] = None,
    icone: str = "💰",
    nome_modulo: str = "Comissão RCA",
) -> None:
    """Renderiza o header navy + título da página + subtítulo.

    Args:
        titulo:     Título grande da página (ex: "Importação de Comissão RCA")
        subtitulo:  Texto cinza menor abaixo do título
        usuario:    Username logado (renderizado no canto direito do header)
        icone:      Emoji ou ícone que aparece ao lado do título
        nome_modulo: Nome do módulo no header (default "Comissão RCA")
    """
    user_html = ""
    if usuario:
        user_html = (
            f'<span class="rofe-user">👤 {usuario}</span>'
            f'<a class="rofe-logout" href="?logout=1">Sair</a>'
        )

    header_html = f"""
    <div class="rofe-header">
        <div class="rofe-header-left">
            <span class="rofe-logo">ROFE</span>
            <span class="rofe-divider">|</span>
            <span class="rofe-app-name">{nome_modulo}</span>
        </div>
        <div class="rofe-header-right">
            {user_html}
        </div>
    </div>

    <div class="rofe-page-title">
        <span class="rofe-icon">{icone}</span>
        <h1>{titulo}</h1>
    </div>
    """
    if subtitulo:
        header_html += f'<p class="rofe-page-subtitle">{subtitulo}</p>'

    st.markdown(header_html, unsafe_allow_html=True)


@contextmanager
def secao(titulo: str, icone: str = "📋"):
    """Renderiza um separador visual de seção (com título + ícone + linha).

    Uso:
        with secao("Parâmetros", icone="⚙️"):
            col1, col2 = st.columns(2)
            ...
    """
    st.markdown(
        f'<div class="rofe-section-title">'
        f'<span class="icon">{icone}</span>{titulo}'
        f'</div>',
        unsafe_allow_html=True,
    )
    yield


def info_card(label: str, valor: str) -> None:
    """Card informativo com label uppercase pequeno + valor grande.

    Use dentro de st.columns() pra criar a fileira de 4 cards do dashboard.
    """
    st.markdown(
        f'<div class="rofe-info-card">'
        f'<div class="rofe-info-card-label">{label}</div>'
        f'<div class="rofe-info-card-value">{valor}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def badge(texto: str, cor: str = "blue") -> str:
    """Retorna HTML de um badge colorido para usar em st.markdown.

    Cores válidas: blue, green, red, yellow, gray, navy.
    """
    cores = {
        "blue":   "#2563eb",
        "green":  "#16a34a",
        "red":    "#dc2626",
        "yellow": "#f59e0b",
        "gray":   "#64748b",
        "navy":   "#1e3a6b",
    }
    bg = cores.get(cor, cor)
    return (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:12px;'
        f'background:{bg};color:white;font-size:12px;font-weight:600;'
        f'margin:2px 4px 2px 0;">{texto}</span>'
    )
