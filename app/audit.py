"""
Auditoria das importações na tabela MariaDB `importacoes` + `importacao_itens`.

Não bloqueia a gravação no Oracle: se a auditoria falhar, log de erro
e segue (try/except no caller). A intenção é rastrear quem importou,
quando, quanto, e os RECNUMs gerados na PCLANC.
"""
from __future__ import annotations
from typing import Optional

import db


# =============================================================================
# Cabeçalho da importação
# =============================================================================
def iniciar_importacao(
    usuario_id: int,
    arquivo_nome: Optional[str],
    total_itens: int,
    valor_total: float,
) -> int:
    """Cria registro em `importacoes` com status='rascunho'.

    Retorna o ID da importação (usado depois pra registrar itens / finalizar).
    """
    return db.execute(
        """
        INSERT INTO importacoes
          (usuario_id, arquivo_nome, total_itens, valor_total, status)
        VALUES (%s, %s, %s, %s, 'rascunho')
        """,
        (usuario_id, arquivo_nome, int(total_itens), float(valor_total)),
    )


def finalizar_importacao(
    importacao_id: int,
    sucesso: bool,
    erro_msg: Optional[str] = None,
) -> None:
    """Atualiza status para 'gravado' ou 'erro' + finalizada_em."""
    status = "gravado" if sucesso else "erro"
    db.execute(
        """
        UPDATE importacoes
           SET status = %s,
               finalizada_em = NOW(),
               erro_msg = %s
         WHERE id = %s
        """,
        (status, erro_msg, int(importacao_id)),
    )


# =============================================================================
# Itens da importação (cada lançamento gravado/tentado)
# =============================================================================
def registrar_lancamentos(
    importacao_id: int,
    lancamentos: list[dict],
    recnums: Optional[list[int]] = None,
    sucesso: bool = True,
    erro_msg: Optional[str] = None,
) -> None:
    """Insere uma linha em `importacao_itens` para cada lançamento.

    Args:
        importacao_id: ID retornado por iniciar_importacao()
        lancamentos:   st.session_state.lancamentos (lista de dicts)
        recnums:       lista paralela de RECNUMs gerados na PCLANC (None se erro)
        sucesso:       True se gravou na Oracle, False se rollback
        erro_msg:      mensagem de erro do Oracle (se sucesso=False)
    """
    if not lancamentos:
        return

    status_item = "gravado" if sucesso else "erro"
    rows = []
    for i, l in enumerate(lancamentos):
        recnum = None
        if recnums and i < len(recnums):
            recnum = recnums[i]
        rows.append((
            int(importacao_id),
            l.get("linha"),                                  # linha do excel
            int(l.get("parcela", 1)),
            int(l["codusur"]),
            l.get("nome_rca"),
            l.get("codfilial"),
            int(l["codconta"]) if l.get("codconta") else None,
            float(l["valor"]),
            l.get("dtlanc"),
            l["dtvenc"],
            l.get("historico"),
            int(recnum) if recnum else None,
            status_item,
            erro_msg if not sucesso else None,
        ))

    db.execute_many(
        """
        INSERT INTO importacao_itens
          (importacao_id, linha_excel, parcela, codusur, nome_rca,
           codfilial, codconta, valor, dtlanc, dtvenc, historico,
           recnum_oracle, status, erro_msg)
        VALUES
          (%s, %s, %s, %s, %s,
           %s, %s, %s, %s, %s, %s,
           %s, %s, %s)
        """,
        rows,
    )


# =============================================================================
# Listagem (pra tela de Histórico)
# =============================================================================
def listar_historico(
    usuario_id: Optional[int] = None,
    limit: int = 100,
) -> list[dict]:
    """Lista importações (todas se admin, ou só do usuário se operador)."""
    base_sql = """
        SELECT i.id, i.usuario_id,
               u.email AS usuario_email,
               u.nome  AS usuario_nome,
               i.arquivo_nome,
               i.total_itens,
               i.valor_total,
               i.status,
               i.iniciada_em,
               i.finalizada_em,
               i.erro_msg
          FROM importacoes i
          JOIN usuarios u ON u.id = i.usuario_id
    """
    if usuario_id is not None:
        return db.fetch_all(
            base_sql + " WHERE i.usuario_id = %s ORDER BY i.iniciada_em DESC LIMIT %s",
            (int(usuario_id), int(limit)),
        )
    return db.fetch_all(
        base_sql + " ORDER BY i.iniciada_em DESC LIMIT %s",
        (int(limit),),
    )


def listar_itens(importacao_id: int) -> list[dict]:
    """Lista todos os itens de uma importação."""
    return db.fetch_all(
        """
        SELECT id, linha_excel, parcela, codusur, nome_rca,
               codfilial, codconta, valor, dtlanc, dtvenc, historico,
               recnum_oracle, status, erro_msg
          FROM importacao_itens
         WHERE importacao_id = %s
         ORDER BY id
        """,
        (int(importacao_id),),
    )
