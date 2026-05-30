# Changelog

## [1.0.0] — 2026-05-20

### Adicionado
- Script `zabbix_audit_export.py` — exportação incremental com controle de cursor
- Script `zabbix_audit_backfill.py` — carga histórica a partir de uma data
- Separação de logs por categoria e mês (hosts, triggers, itens, templates, usuários, manutenção, discovery, dashboard, outros)
- Resolução de hostname para registros de triggers via join `triggers → functions → items → hosts`
- Filtro de usuários reais via `INNER JOIN users` e `roleid IS NOT NULL`
- Configuração de cron (06h, 12h, 18h)
- Configuração de logrotate (mensal, 24 meses, compressão .gz)
- Backfill histórico desde 01/01/2026 — 780.602 registros exportados no ambiente Sabin
- Documentação técnica completa (README, INSTALL, FORMATO_DOS_LOGS)

### Corrigido
- Conexão via socket Unix para peer auth (DB_HOST vazio)
- Filtro `u.type` substituído por `u.roleid IS NOT NULL` (compatibilidade Zabbix 6.x+)
- Remoção de arquivo geral consolidado para evitar duplicação de registros
