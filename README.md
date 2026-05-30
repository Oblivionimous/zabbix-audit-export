# zabbix-audit-export

Sistema de exportação e retenção de longo prazo do auditlog do Zabbix para arquivos `.log` rotativos.

---

## Problema

O Zabbix purga automaticamente o auditlog pelo housekeeper (padrão ~6 meses), impossibilitando rastreabilidade de ações históricas como criação de hosts, inativação de triggers e alterações de configuração.

## Solução

Scripts Python que consultam o banco PostgreSQL do Zabbix e exportam os registros para arquivos `.log` separados por **categoria** e **mês**, com agendamento via cron e rotação via logrotate (retenção de 24 meses).

---

## Funcionalidades

- Exportação incremental com controle de cursor (sem duplicatas)
- Separação automática por categoria (hosts, triggers, itens, templates, usuários, manutenção, discovery)
- Hostname resolvido para triggers (via join `triggers → functions → items → hosts`)
- Filtro automático de usuários reais (exclui sistema, contas sem role)
- Backfill histórico a partir de uma data específica
- Logrotate com compressão `.gz` e retenção de 24 meses
- Formato de log legível e compatível com `grep` e `zgrep`

---

## Estrutura do Projeto

```
zabbix-audit-export/
├── scripts/
│   ├── zabbix_audit_export.py      # Exportação incremental (roda via cron)
│   └── zabbix_audit_backfill.py    # Carga histórica a partir de uma data
├── config/
│   ├── zabbix-audit.cron           # Configuração do cron
│   └── zabbix-audit.logrotate      # Configuração do logrotate
├── docs/
│   └── FORMATO_DOS_LOGS.md         # Documentação do formato das linhas de log
├── README.md
└── INSTALL.md
```

---

## Pré-requisitos

- Python 3.x
- psycopg2: `pip3 install psycopg2-binary --break-system-packages`
- Acesso ao servidor PostgreSQL do Zabbix (peer auth via `sudo -u postgres`)
- Linux com systemd/cron e logrotate

## Compatibilidade

Testado com:
- Zabbix 6.x e 7.x
- PostgreSQL 16
- Ubuntu 24.04 LTS

---

## Instalação Rápida

Veja [INSTALL.md](INSTALL.md) para instruções completas.

```bash
# 1. Copiar scripts
mkdir -p /opt/zabbix-audit
cp scripts/zabbix_audit_export.py scripts/zabbix_audit_backfill.py /opt/zabbix-audit/

# 2. Criar diretório de logs
mkdir -p /var/log/zabbix-audit/archive
chown -R postgres:postgres /var/log/zabbix-audit
chmod 750 /var/log/zabbix-audit

# 3. Instalar dependência
pip3 install psycopg2-binary --break-system-packages

# 4. Testar
sudo -u postgres python3 /opt/zabbix-audit/zabbix_audit_export.py

# 5. Configurar cron e logrotate
cp config/zabbix-audit.cron /etc/cron.d/zabbix-audit
cp config/zabbix-audit.logrotate /etc/logrotate.d/zabbix-audit

# 6. Backfill histórico (opcional)
sudo -u postgres python3 /opt/zabbix-audit/zabbix_audit_backfill.py 2026-01-01
```

---

## Exemplo de Saída

```
[2026-05-08 14:46:04] USUARIO=hugodeolindo IP=10.96.32.57 TIPO=Trigger ACAO=ATUALIZOU OBJETO=Indisponivel por ping ICMP HOST=dfbsbsaandcswpa01 | DETALHE: trigger.status => 1,"0
[2026-01-09 13:27:44] USUARIO=mauro.p IP=10.96.40.147 TIPO=Host ACAO=CRIOU OBJETO=dcsaansrvmirror02 - Banco Cache teste HOST=dcsaansrvmirror02 - Banco Cache teste
[2026-02-13 10:31:09] USUARIO=werickvl IP=10.96.40.149 TIPO=Manutenção ACAO=CRIOU OBJETO=DCSAANSRVPHAPP3 - Protheus aplicação.. | DETALHE: maintenance.name => ADICIONOU: "DCSAANSRVPHAPP3...
```

---

## Pesquisa nos Logs

```bash
# Todas as ações de um usuário em triggers
grep "hugodeolindo" /var/log/zabbix-audit/audit_triggers_2026-*.log

# Triggers inativadas no mês
grep "trigger.status => 1" /var/log/zabbix-audit/audit_triggers_2026-05.log

# Hosts criados ou deletados
grep -E "ACAO=CRIOU|ACAO=DELETOU" /var/log/zabbix-audit/audit_hosts_2026-05.log

# Busca em arquivos comprimidos
zgrep "hugodeolindo" /var/log/zabbix-audit/archive/audit_triggers_*.log.gz

# Excluir usuários específicos
grep -v -E "USUARIO=fulano |USUARIO=ciclano " /var/log/zabbix-audit/audit_triggers_2026-*.log

# Contar triggers inativadas por usuário
grep "trigger.status => 1" /var/log/zabbix-audit/audit_triggers_2026-05.log \
  | grep -oP 'USUARIO=\S+' | sort | uniq -c | sort -rn
```

---

## Categorias de Log

| Arquivo | Conteúdo |
|---------|----------|
| `audit_hosts_YYYY-MM.log` | Criação, atualização e exclusão de hosts |
| `audit_triggers_YYYY-MM.log` | Alterações em triggers (ativação, inativação) |
| `audit_usuarios_YYYY-MM.log` | Ações em usuários, grupos e roles |
| `audit_templates_YYYY-MM.log` | Alterações em templates |
| `audit_itens_YYYY-MM.log` | Alterações em itens e protótipos |
| `audit_manutencao_YYYY-MM.log` | Janelas de manutenção |
| `audit_discovery_YYYY-MM.log` | Regras de descoberta e LLD |
| `audit_dashboard_YYYY-MM.log` | Dashboards |
| `audit_outros_YYYY-MM.log` | Demais recursos |

---

## Licença

MIT — livre para uso e adaptação.
