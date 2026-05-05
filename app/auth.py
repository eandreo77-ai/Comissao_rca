"""
Autenticação por OTP via email (passwordless).

Fluxo:
  1. usuário digita email → solicitar_codigo(email)
  2. sistema gera código aleatório de 20 chars, salva em auth_tokens, envia email
  3. usuário recebe email e digita código
  4. validar_codigo(email, codigo) → marca usado, cria sessão Streamlit
  5. gate_login() bloqueia o app se não houver sessão

Usuários são pré-cadastrados pelo admin (ver pages/2_Usuarios.py).
"""
from __future__ import annotations

import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import streamlit as st

import db


# =============================================================================
# Configurações
# =============================================================================
OTP_TTL_MINUTES = int(os.environ.get("OTP_TTL_MINUTES", "10"))
OTP_LENGTH = 20


# =============================================================================
# Geração e envio do código
# =============================================================================
def _gerar_codigo(tamanho: int = OTP_LENGTH) -> str:
    """Código urlsafe (letras + dígitos + - _) de tamanho fixo."""
    # token_urlsafe gera ~tamanho * 1.3 chars; cortamos pra exato.
    return secrets.token_urlsafe(tamanho)[:tamanho]


def solicitar_codigo(email: str, ip: Optional[str] = None) -> tuple[bool, str]:
    """Procura usuário pelo email; se ativo, gera código e envia por email.

    Retorna mensagem genérica em caso de email não encontrado, pra não
    revelar se o email está cadastrado.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Email inválido."

    user = db.fetch_one(
        "SELECT id, nome, ativo FROM usuarios WHERE LOWER(email) = %s",
        (email,),
    )
    msg_generica = "Se o email estiver cadastrado, você receberá um código em instantes."

    if not user or not user["ativo"]:
        # Não revela. Mas log no servidor pra debug.
        print(f"[auth] solicitação para email não cadastrado/inativo: {email}")
        return True, msg_generica

    # Gera código + grava
    codigo = _gerar_codigo()
    expira = datetime.now() + timedelta(minutes=OTP_TTL_MINUTES)
    db.execute(
        """
        INSERT INTO auth_tokens (usuario_id, codigo, dt_expira, ip_origem)
        VALUES (%s, %s, %s, %s)
        """,
        (user["id"], codigo, expira, ip),
    )

    # Envia email
    try:
        _enviar_email_otp(email, codigo, user["nome"])
    except Exception as e:
        # Não revela detalhe SMTP pro front. Log server-side.
        print(f"[auth] falha enviando email para {email}: {e}")
        return False, "Falha ao enviar o email. Tente novamente em instantes."

    return True, msg_generica


def _enviar_email_otp(to_email: str, codigo: str, nome: str) -> None:
    """SMTP via vars de ambiente. Lança exceção se falhar."""
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    from_email = os.environ.get("EMAIL_FROM", user)

    if not host or not user or not password:
        raise RuntimeError(
            "Variáveis SMTP não configuradas (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)."
        )

    msg = MIMEMultipart()
    msg["From"] = f"Comissão RCA - ROFE <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = "Seu código de acesso - Comissão RCA"

    body_text = (
        f"Olá {nome},\n\n"
        f"Seu código de acesso ao sistema Comissão RCA:\n\n"
        f"    {codigo}\n\n"
        f"Esse código é válido por {OTP_TTL_MINUTES} minutos e só pode ser usado 1 vez.\n\n"
        f"Se você não solicitou esse código, ignore este email.\n\n"
        f"-- ROFE Distribuidora\n"
    )
    body_html = f"""\
<html><body style="font-family:Arial,sans-serif;color:#111827;">
  <p>Olá <b>{nome}</b>,</p>
  <p>Seu código de acesso ao sistema <b>Comissão RCA</b>:</p>
  <p style="font-size:22px;font-weight:600;background:#f3f4f6;
            padding:14px 24px;border-radius:8px;letter-spacing:1px;
            font-family:'Courier New',monospace;display:inline-block;">
    {codigo}
  </p>
  <p style="color:#6b7280;font-size:13px;">
    Válido por {OTP_TTL_MINUTES} minutos. Pode ser usado uma única vez.<br>
    Se você não solicitou esse código, ignore este email.
  </p>
  <hr style="border:0;border-top:1px solid #e5e7eb;margin:20px 0;">
  <p style="color:#9ca3af;font-size:12px;">ROFE Distribuidora</p>
</body></html>
"""
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        server.login(user, password)
        server.send_message(msg)


# =============================================================================
# Validação do código
# =============================================================================
def validar_codigo(email: str, codigo: str) -> Optional[dict]:
    """Retorna dict do usuário se código válido, senão None."""
    email = (email or "").strip().lower()
    codigo = (codigo or "").strip()
    if not email or not codigo:
        return None

    row = db.fetch_one(
        """
        SELECT t.id  AS token_id,
               u.id  AS user_id,
               u.email,
               u.nome,
               u.perfil
          FROM auth_tokens t
          JOIN usuarios u ON u.id = t.usuario_id
         WHERE LOWER(u.email) = %s
           AND t.codigo  = %s
           AND t.usado   = 0
           AND t.dt_expira > NOW()
           AND u.ativo   = 1
         ORDER BY t.dt_gerado DESC
         LIMIT 1
        """,
        (email, codigo),
    )
    if not row:
        return None

    # Marca código como usado e atualiza ultimo_login
    db.execute("UPDATE auth_tokens SET usado = 1 WHERE id = %s", (row["token_id"],))
    db.execute("UPDATE usuarios SET ultimo_login = NOW() WHERE id = %s", (row["user_id"],))

    return {
        "id": row["user_id"],
        "email": row["email"],
        "nome": row["nome"],
        "perfil": row["perfil"],
    }


# =============================================================================
# Sessão (st.session_state)
# =============================================================================
def usuario_logado() -> Optional[dict]:
    """Retorna dict {id,email,nome,perfil} se logado, senão None."""
    if st.session_state.get("user_id"):
        return {
            "id":     st.session_state.get("user_id"),
            "email":  st.session_state.get("user_email"),
            "nome":   st.session_state.get("user_nome"),
            "perfil": st.session_state.get("user_perfil"),
        }
    return None


def is_admin() -> bool:
    u = usuario_logado()
    return bool(u and u["perfil"] == "admin")


def logout() -> None:
    for k in (
        "user_id", "user_email", "user_nome", "user_perfil",
        "codigo_enviado_para",
    ):
        if k in st.session_state:
            del st.session_state[k]


# =============================================================================
# Gate de login (UI)
# =============================================================================
def gate_login() -> None:
    """Se não logado, renderiza tela de login e bloqueia o resto do app.

    Trata também o ?logout=1 do header.
    """
    # Logout via querystring (link "Sair" do header passa ?logout=1)
    if st.query_params.get("logout"):
        logout()
        st.query_params.clear()
        st.rerun()

    if usuario_logado():
        return  # liberado

    # ── Tela de login ──────────────────────────────────────────────────────
    from styles import aplicar_visual, header
    aplicar_visual()
    header(
        titulo="Comissão RCA",
        subtitulo="Acesso restrito — informe seu email corporativo",
        icone="🔐",
        nome_modulo="Comissão RCA",
    )

    container = st.container()

    with container:
        if "codigo_enviado_para" not in st.session_state:
            # ─── ETAPA 1: pede email ─────────────────────────────────────
            st.markdown("#### 1. Informe seu email")
            st.markdown(
                '<p style="color:#6b7280;font-size:13px;">'
                'Você receberá um código de 20 caracteres válido por '
                f'{OTP_TTL_MINUTES} minutos.'
                '</p>',
                unsafe_allow_html=True,
            )
            with st.form("login_email_form", clear_on_submit=False):
                email = st.text_input(
                    "Email",
                    placeholder="seu.email@rofedistribuidora.com.br",
                ).strip()
                enviado = st.form_submit_button("Enviar código", type="primary")

                if enviado:
                    ok, msg = solicitar_codigo(email)
                    if ok:
                        st.session_state.codigo_enviado_para = email
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        else:
            # ─── ETAPA 2: pede código ────────────────────────────────────
            email_atual = st.session_state.codigo_enviado_para
            st.markdown("#### 2. Informe o código recebido")
            st.markdown(
                f'<p style="color:#6b7280;font-size:13px;">'
                f'Código enviado para <b>{email_atual}</b>. '
                f'Confira sua caixa de entrada (e o spam).'
                f'</p>',
                unsafe_allow_html=True,
            )
            with st.form("login_codigo_form"):
                codigo = st.text_input(
                    "Código (20 caracteres)",
                    max_chars=OTP_LENGTH,
                    placeholder="cole aqui o código do email",
                ).strip()
                col_a, col_b, _ = st.columns([1, 1, 3])
                validar = col_a.form_submit_button("Validar", type="primary")
                trocar = col_b.form_submit_button("Trocar email")

                if trocar:
                    del st.session_state.codigo_enviado_para
                    st.rerun()
                elif validar:
                    user = validar_codigo(email_atual, codigo)
                    if user:
                        st.session_state.user_id = user["id"]
                        st.session_state.user_email = user["email"]
                        st.session_state.user_nome = user["nome"]
                        st.session_state.user_perfil = user["perfil"]
                        del st.session_state.codigo_enviado_para
                        st.rerun()
                    else:
                        st.error("Código inválido ou expirado.")

    st.stop()  # bloqueia execução do resto do script
