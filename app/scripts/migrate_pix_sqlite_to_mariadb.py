"""
Migra dados do SQLite local (app/data/pix.db) pro MariaDB (rca_pix + rca_ignorar).

Roda dentro do container, com app no PYTHONPATH (pra acessar db.py):
    docker compose exec app python /code/app/scripts/migrate_pix_sqlite_to_mariadb.py

Ou no host, definindo MARIADB_* nas env vars:
    python migrate_pix_sqlite_to_mariadb.py /caminho/para/pix.db

Idempotente — ON DUPLICATE KEY UPDATE garante que rodar 2x não duplica.
"""
from __future__ import annotations

import os
import sqlite3
import sys

# Permite importar db.py
sys.path.insert(0, "/code/app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


def main(sqlite_path: str = "/code/app/data/pix.db") -> None:
    if not os.path.exists(sqlite_path):
        print(f"[skip] {sqlite_path} não existe — nada a migrar")
        return

    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row

    # ── rca_pix ────────────────────────────────────────────────────────────
    print("=== Migrando rca_pix ===")
    n_pix = 0
    n_erros = 0
    try:
        for row in con.execute("SELECT codrca, nome_rca, chave_pix, tipo_chave, dt_atualizacao, usuario FROM rca_pix"):
            try:
                db.execute(
                    """
                    INSERT INTO rca_pix
                      (codrca, nome_rca, chave_pix, tipo_chave, usuario, dt_atualizacao)
                    VALUES
                      (%s, %s, %s, %s, %s, COALESCE(%s, NOW()))
                    ON DUPLICATE KEY UPDATE
                        nome_rca       = VALUES(nome_rca),
                        chave_pix      = VALUES(chave_pix),
                        tipo_chave     = VALUES(tipo_chave),
                        usuario        = VALUES(usuario),
                        dt_atualizacao = VALUES(dt_atualizacao)
                    """,
                    (row["codrca"], row["nome_rca"], row["chave_pix"],
                     (row["tipo_chave"] or "").upper(),
                     row["usuario"], row["dt_atualizacao"]),
                )
                n_pix += 1
            except Exception as e:
                n_erros += 1
                print(f"  erro CODRCA {row['codrca']}: {e}")
        print(f"  OK: {n_pix} chaves PIX migradas ({n_erros} erros)")
    except sqlite3.OperationalError as e:
        print(f"  rca_pix não existe no SQLite: {e}")

    # ── rca_ignorar ────────────────────────────────────────────────────────
    print()
    print("=== Migrando rca_ignorar ===")
    n_ign = 0
    n_erros = 0
    try:
        for row in con.execute("SELECT codrca, motivo, dt_inclusao FROM rca_ignorar"):
            try:
                db.execute(
                    """
                    INSERT INTO rca_ignorar
                      (codrca, motivo, dt_inclusao)
                    VALUES
                      (%s, %s, COALESCE(%s, NOW()))
                    ON DUPLICATE KEY UPDATE
                        motivo      = VALUES(motivo),
                        dt_inclusao = VALUES(dt_inclusao)
                    """,
                    (row["codrca"], row["motivo"], row["dt_inclusao"]),
                )
                n_ign += 1
            except Exception as e:
                n_erros += 1
                print(f"  erro CODRCA {row['codrca']}: {e}")
        print(f"  OK: {n_ign} ignorados migrados ({n_erros} erros)")
    except sqlite3.OperationalError as e:
        print(f"  rca_ignorar não existe no SQLite: {e}")

    con.close()
    print()
    print("[OK] Migração concluída.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/code/app/data/pix.db"
    main(path)
