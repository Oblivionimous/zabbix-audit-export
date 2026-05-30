# Instalação e Configuração

## 1. Pré-requisitos

```bash
# Instalar dependência Python
pip3 install psycopg2-binary --break-system-packages
```

## 2. Copiar Scripts

```bash
mkdir -p /opt/zabbix-audit
cp scripts/zabbix_audit_export.py scripts/zabbix_audit_backfill.py /opt/zabbix-audit/
chmod 750 /opt/zabbix-audit/*.py
```

## 3. Criar Diretório de Logs

```bash
mkdir -p /var/log/zabbix-audit/archive
chown -R postgres:postgres /var/log/zabbix-audit
chmod 750 /var/log/zabbix-audit
chmod 750 /var/log/zabbix-audit/archive
```

## 4. Configurar o Script

Edite as variáveis no início de `/opt/zabbix-audit/zabbix_audit_export.py`:

```python
DB_HOST     = ""          # vazio = socket Unix (peer auth com sudo -u postgres)
DB_PORT     = 5432
DB_NAME     = "zabbix"   # nome do banco do Zabbix
DB_USER     = "postgres"
DB_PASSWORD = ""          # vazio = peer auth sem senha
LOG_DIR     = "/var/log/zabbix-audit"
CURSOR_FILE = "/var/log/zabbix-audit/.last_clock"
```

> Se o banco não usa peer auth, informe `DB_HOST = "localhost"` e `DB_PASSWORD = "sua_senha"`.

## 5. Testar Manualmente

```bash
# Com peer auth (recomendado)
sudo -u postgres python3 /opt/zabbix-audit/zabbix_audit_export.py

# Com senha
python3 /opt/zabbix-audit/zabbix_audit_export.py
```

Saída esperada:
```
[2026-05-20 18:10:40] Iniciando exportação. Último clock: 0
[2026-05-20 18:10:41] Exportação concluída. 1234 registros novos.
           hosts          : 45 registros
           triggers       : 120 registros
           ...
```

## 6. Configurar Cron

```bash
cp config/zabbix-audit.cron /etc/cron.d/zabbix-audit
chmod 644 /etc/cron.d/zabbix-audit

# Verificar
cat /etc/cron.d/zabbix-audit
```

## 7. Configurar Logrotate

```bash
cp config/zabbix-audit.logrotate /etc/logrotate.d/zabbix-audit

# Testar configuração (sem executar)
logrotate -d /etc/logrotate.d/zabbix-audit

# Forçar execução para validar
logrotate -f /etc/logrotate.d/zabbix-audit
```

## 8. Backfill Histórico (Opcional)

Para popular os logs com dados históricos desde uma data específica:

```bash
sudo -u postgres python3 /opt/zabbix-audit/zabbix_audit_backfill.py 2026-01-01
```

> O backfill respeita a data real de cada evento — registros de fevereiro vão para `audit_*_2026-02.log`, não para o arquivo do mês atual.

> O auditlog do Zabbix só retém dados pelo período configurado no housekeeper. Consulte o registro mais antigo disponível antes de definir a data de backfill:
> ```sql
> SELECT TO_TIMESTAMP(MIN(clock)) FROM auditlog;
> ```

## 9. Verificar Instalação

```bash
# Ver logs gerados
ls -lh /var/log/zabbix-audit/

# Ver tamanho total
du -sh /var/log/zabbix-audit/

# Verificar cursor
cat /var/log/zabbix-audit/.last_clock

# Ver log de execução do cron
tail -20 /var/log/zabbix-audit/cron.log
```

---

## Solução de Problemas

### Erro: `PermissionError: [Errno 13] Permission denied: '/var/log/zabbix-audit'`

O diretório precisa ser criado como root e a ownership passada para postgres:
```bash
mkdir -p /var/log/zabbix-audit/archive
chown -R postgres:postgres /var/log/zabbix-audit
```

### Erro: `fe_sendauth: no password supplied`

O script está tentando conectar via TCP. Deixe `DB_HOST = ""` para forçar conexão via socket Unix com peer auth.

### Erro: `column u.type does not exist`

Zabbix 6.x+ não tem a coluna `type` na tabela `users` — o tipo do usuário foi migrado para a tabela `role`. Use a versão atual do script que filtra por `roleid IS NOT NULL`.

### Cron não executa

Verifique se o arquivo tem permissão correta e não tem linha em branco no final:
```bash
chmod 644 /etc/cron.d/zabbix-audit
cat -A /etc/cron.d/zabbix-audit  # não deve ter ^M (CRLF)
```
