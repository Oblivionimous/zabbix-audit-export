#!/usr/bin/env python3
# =============================================================================
# zabbix_audit_backfill.py
# Importa histórico do auditlog desde uma data específica
# Uso: python3 zabbix_audit_backfill.py 2026-01-01
# =============================================================================

import psycopg2
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zabbix_audit_export import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    LOG_DIR, CURSOR_FILE,
    get_categoria, formatar_linha, garantir_dirs, salvar_cursor
)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 zabbix_audit_backfill.py YYYY-MM-DD")
        sys.exit(1)

    try:
        data_inicio = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print("Formato inválido. Use YYYY-MM-DD")
        sys.exit(1)

    clock_inicio = int(data_inicio.timestamp())
    agora        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    garantir_dirs()
    print(f"[{agora}] Backfill desde {sys.argv[1]} (clock >= {clock_inicio})")

    try:
        conn_args = {"port": DB_PORT, "dbname": DB_NAME, "user": DB_USER}
        if DB_HOST:
            conn_args["host"] = DB_HOST
        if DB_PASSWORD:
            conn_args["password"] = DB_PASSWORD
        conn = psycopg2.connect(**conn_args)
        cur  = conn.cursor()
    except Exception as e:
        print(f"[ERRO] Falha na conexão: {e}")
        sys.exit(1)

    query = """
        SELECT
            a.clock,
            u.username,
            a.ip,
            a.resourcetype,
            a.action,
            COALESCE(NULLIF(a.resourcename, ''), ''),
            a.resourceid,
            a.details,
            CASE
                WHEN a.resourcetype = 4 THEN
                    (SELECT h.host FROM hosts h WHERE h.hostid = a.resourceid LIMIT 1)
                WHEN a.resourcetype IN (13, 31) THEN
                    (SELECT DISTINCT h.host
                     FROM triggers t
                     JOIN functions f ON f.triggerid = t.triggerid
                     JOIN items i     ON i.itemid = f.itemid
                     JOIN hosts h     ON h.hostid = i.hostid
                     WHERE t.triggerid = a.resourceid
                     LIMIT 1)
                ELSE NULL
            END AS hostname
        FROM auditlog a
        INNER JOIN users u ON a.userid = u.userid
        WHERE a.clock >= %s
          AND a.userid <> 0
          AND u.username IS NOT NULL
          AND u.username <> ''
          AND u.roleid IS NOT NULL
        ORDER BY a.clock ASC
    """

    cur.execute(query, (clock_inicio,))
    rows = cur.fetchall()

    if not rows:
        print("Nenhum registro encontrado.")
        conn.close()
        return

    print(f"[{agora}] {len(rows)} registros encontrados. Gravando...")

    logs_abertos = {}
    contadores   = {}
    max_clock    = clock_inicio

    try:
        for row in rows:
            clock     = row[0]
            categoria = get_categoria(row[3])
            mes_ano   = datetime.fromtimestamp(clock).strftime("%Y-%m")
            chave     = f"{categoria}_{mes_ano}"

            if chave not in logs_abertos:
                caminho = os.path.join(LOG_DIR, f"audit_{chave}.log")
                logs_abertos[chave] = open(caminho, "a", encoding="utf-8")
                contadores[chave]   = 0

            logs_abertos[chave].write(formatar_linha(row))
            contadores[chave] += 1

            if clock > max_clock:
                max_clock = clock
    finally:
        for f in logs_abertos.values():
            f.close()

    salvar_cursor(max_clock)
    conn.close()

    print(f"\nBackfill concluído! Arquivos em {LOG_DIR}:")
    for chave, qtd in sorted(contadores.items()):
        print(f"  audit_{chave}.log  ->  {qtd} registros")


if __name__ == "__main__":
    main()
