#!/usr/bin/env python3
# =============================================================================
# zabbix_audit_export.py
# Exporta o auditlog do Zabbix (PostgreSQL) para arquivos .log rotativos
# Roda 3x ao dia via cron (06:00, 12:00 e 18:00)
# Inclui hostname para triggers e hosts
# Para buscar: grep "termo" /var/log/zabbix-audit/audit_*.log
# =============================================================================

import psycopg2
import os
import sys
from datetime import datetime

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
DB_HOST     = ""        # vazio = socket Unix (peer auth com sudo -u postgres)
DB_PORT     = 5432
DB_NAME     = "zabbix"
DB_USER     = "postgres"
DB_PASSWORD = ""

LOG_DIR     = "/var/log/zabbix-audit"
CURSOR_FILE = "/var/log/zabbix-audit/.last_clock"
# =============================================================================

RESOURCE_TYPES = {
    0:  "Usuário",        3:  "Tipo de Mídia",    4:  "Host",
    5:  "Ação",           6:  "Gráfico",           11: "Grupo de Usuários",
    13: "Trigger",        14: "Grupo de Hosts",    15: "Item",
    16: "Imagem",         17: "Mapeamento de Valor", 18: "Serviço",
    19: "Mapa",           22: "Cenário Web",       23: "Regra de Descoberta",
    25: "Script",         26: "Proxy",             27: "Manutenção",
    28: "Expressão Regular", 29: "Macro",          30: "Template",
    31: "Protótipo de Trigger", 32: "Mapeamento de Ícone", 33: "Dashboard",
    34: "Correlação de Eventos", 35: "Protótipo de Gráfico", 36: "Protótipo de Item",
    37: "Protótipo de Host", 38: "Autorregistro",  39: "Módulo",
    40: "Configurações",  41: "Housekeeping",      42: "Autenticação",
    43: "Dashboard de Template", 44: "Role de Usuário", 45: "Token de API",
    46: "Relatório Agendado", 47: "Nó HA",         48: "SLA",
    49: "Diretório de Usuários", 50: "Grupo de Templates", 51: "Conector",
    52: "Regra de LLD",   53: "Histórico",
}

ACTIONS = {
    0:  "CRIOU",    1:  "ATUALIZOU",   2:  "DELETOU",
    4:  "LOGOUT",   7:  "EXECUTOU",    8:  "LOGIN",
    9:  "FALHA NO LOGIN", 10: "LIMPOU HISTÓRICO",
    11: "ATUALIZOU CONFIG", 12: "PUSH",
}

CATEGORIAS = {
    "hosts":      [4],
    "triggers":   [13, 31],
    "usuarios":   [0, 11, 44],
    "templates":  [30, 43],
    "itens":      [15, 36],
    "manutencao": [27],
    "discovery":  [23, 52],
    "dashboard":  [33],
    "outros":     [],
}


def get_categoria(resourcetype):
    for cat, tipos in CATEGORIAS.items():
        if resourcetype in tipos:
            return cat
    return "outros"


def limpar_details(details):
    if not details:
        return ""
    r = details
    r = r.replace('":["update",', ' => ')
    r = r.replace('":["add",',    ' => ADICIONOU: ')
    r = r.replace('":["delete"]', ' => REMOVEU')
    r = r.replace('","',          ' | ERA: ')
    r = r.replace('{"',           '')
    r = r.replace('"]}',          '')
    r = r.replace('"}',           '')
    r = r.replace('"]',           '')
    r = r.replace('\\r\\n', ' ').replace('\\n', ' ').replace('\\t', ' ')
    while '  ' in r:
        r = r.replace('  ', ' ')
    return r.strip()


def ler_cursor():
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val.isdigit() else 0
    return 0


def salvar_cursor(clock):
    with open(CURSOR_FILE, "w") as f:
        f.write(str(clock))


def garantir_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(LOG_DIR, "archive"), exist_ok=True)


def abrir_log(categoria):
    mes_ano = datetime.now().strftime("%Y-%m")
    caminho = os.path.join(LOG_DIR, f"audit_{categoria}_{mes_ano}.log")
    return open(caminho, "a", encoding="utf-8")


def formatar_linha(row):
    clock, username, ip, resourcetype, action, resourcename, resourceid, details, hostname = row
    data_hora    = datetime.fromtimestamp(clock).strftime("%Y-%m-%d %H:%M:%S")
    tipo_recurso = RESOURCE_TYPES.get(resourcetype, f"Desconhecido({resourcetype})")
    acao         = ACTIONS.get(action, f"OUTRO({action})")
    objeto       = resourcename if resourcename else f"ID:{resourceid}"
    detalhe      = limpar_details(details)
    ip_str       = ip if ip else "-"

    linha = (
        f"[{data_hora}] USUARIO={username} IP={ip_str} "
        f"TIPO={tipo_recurso} ACAO={acao} OBJETO={objeto}"
    )
    if hostname:
        linha += f" HOST={hostname}"
    if detalhe:
        linha += f" | DETALHE: {detalhe}"
    return linha + "\n"


def main():
    garantir_dirs()
    ultimo_clock = ler_cursor()
    agora        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{agora}] Iniciando exportação. Último clock: {ultimo_clock}")

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

    # Subquery para pegar o hostname:
    # - Se for Host (resourcetype=4): pega direto da tabela hosts
    # - Se for Trigger (resourcetype=13/31): cruza trigger->functions->items->hosts
    #   usa DISTINCT ON para evitar duplicatas por trigger vinculada a múltiplos hosts
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
        WHERE a.clock > %s
          AND a.userid <> 0
          AND u.username IS NOT NULL
          AND u.username <> ''
          AND u.roleid IS NOT NULL
        ORDER BY a.clock ASC
    """

    try:
        cur.execute(query, (ultimo_clock,))
        rows = cur.fetchall()
    except Exception as e:
        print(f"[ERRO] Falha na query: {e}")
        conn.close()
        sys.exit(1)

    if not rows:
        print(f"[{agora}] Nenhum registro novo encontrado.")
        conn.close()
        return

    contadores   = {}
    max_clock    = ultimo_clock
    logs_abertos = {}

    try:
        for row in rows:
            clock     = row[0]
            categoria = get_categoria(row[3])

            if categoria not in logs_abertos:
                logs_abertos[categoria] = abrir_log(categoria)
                contadores[categoria]   = 0

            logs_abertos[categoria].write(formatar_linha(row))
            contadores[categoria] += 1

            if clock > max_clock:
                max_clock = clock
    finally:
        for f in logs_abertos.values():
            f.close()

    salvar_cursor(max_clock)
    conn.close()

    total = sum(contadores.values())
    print(f"[{agora}] Exportação concluída. {total} registros novos.")
    for cat, qtd in sorted(contadores.items()):
        print(f"           {cat:<15}: {qtd} registros")


if __name__ == "__main__":
    main()
