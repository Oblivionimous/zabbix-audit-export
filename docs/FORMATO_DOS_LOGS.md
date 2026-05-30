# Formato dos Arquivos de Log

## Estrutura de cada linha

```
[YYYY-MM-DD HH:MM:SS] USUARIO=x IP=x TIPO=x ACAO=x OBJETO=x HOST=x | DETALHE: x
```

| Campo | Descrição |
|-------|-----------|
| `[timestamp]` | Data e hora do evento no formato `YYYY-MM-DD HH:MM:SS` |
| `USUARIO=` | Username do usuário que executou a ação |
| `IP=` | Endereço IP de origem da sessão |
| `TIPO=` | Tipo de recurso modificado (ver tabela abaixo) |
| `ACAO=` | Ação executada (ver tabela abaixo) |
| `OBJETO=` | Nome do recurso modificado |
| `HOST=` | Hostname vinculado (disponível para triggers e hosts) |
| `DETALHE=` | Campos alterados com valor novo e valor anterior |

---

## Tipos de Recurso (TIPO=)

| Valor | Descrição |
|-------|-----------|
| `Host` | Host do Zabbix |
| `Trigger` | Trigger |
| `Protótipo de Trigger` | Trigger criada por LLD |
| `Item` | Item de coleta |
| `Protótipo de Item` | Item criado por LLD |
| `Template` | Template |
| `Usuário` | Usuário do Zabbix |
| `Grupo de Usuários` | Grupo de usuários |
| `Role de Usuário` | Perfil/role de usuário |
| `Manutenção` | Janela de manutenção |
| `Regra de Descoberta` | Regra de LLD |
| `Regra de LLD` | Regra de LLD (alias) |
| `Dashboard` | Dashboard |
| `Grupo de Hosts` | Grupo de hosts |
| `Macro` | Macro global ou de host |
| `Script` | Script executado manualmente |
| `Configurações` | Configurações globais do Zabbix |

---

## Ações (ACAO=)

| Valor | Descrição |
|-------|-----------|
| `CRIOU` | Recurso criado |
| `ATUALIZOU` | Recurso atualizado |
| `DELETOU` | Recurso deletado |
| `EXECUTOU` | Script executado manualmente |
| `LOGIN` | Login realizado |
| `LOGOUT` | Logout realizado |
| `FALHA NO LOGIN` | Tentativa de login com falha |
| `LIMPOU HISTÓRICO` | Histórico de item limpo |
| `ATUALIZOU CONFIG` | Configurações globais alteradas |

---

## Interpretando o campo DETALHE

O campo DETALHE mostra os campos alterados no formato `campo => NOVO_VALOR | ERA: VALOR_ANTERIOR`.

### Trigger inativada
```
trigger.status => 1,"0
```
- `1` = novo valor (inativo)
- `0` = valor anterior (ativo)

### Trigger reativada
```
trigger.status => 0,"1
```
- `0` = novo valor (ativo)
- `1` = valor anterior (inativo)

### Host inativado
```
host.status => 1,"0
```

### Descrição de host atualizada
```
host.description => "Nova descrição | ERA: Descrição anterior
```

### Item inativado
```
item.status => 1 | ERA: 0
```

### Manutenção criada
```
maintenance.name => ADICIONOU: "Nome da manutenção,"maintenance.active_since => ADICIONOU: "1234567890,...
```

---

## Exemplos Reais

### Trigger inativada em massa
```
[2026-05-08 14:46:04] USUARIO=hugodeolindo IP=10.96.32.57 TIPO=Trigger ACAO=ATUALIZOU OBJETO=Indisponivel por ping ICMP HOST=dfbsbsaandcswpa01 | DETALHE: trigger.status => 1,"0
[2026-05-08 14:46:04] USUARIO=hugodeolindo IP=10.96.32.57 TIPO=Trigger ACAO=ATUALIZOU OBJETO=Alta perda de ping ICMP HOST=dfbsbsaandcswpa01 | DETALHE: trigger.status => 1,"0
[2026-05-08 14:46:04] USUARIO=hugodeolindo IP=10.96.32.57 TIPO=Trigger ACAO=ATUALIZOU OBJETO=Sem coleta de dados SNMP HOST=dfbsbsaandcswpa01 | DETALHE: trigger.status => 1,"0
```

### Host criado
```
[2026-01-09 13:27:44] USUARIO=hugodeolindo IP=10.96.40.136 TIPO=Host ACAO=CRIOU OBJETO=DF-BSB-DIGITAL NOROESTE HOST=DF-BSB-DIGITAL NOROESTE
```

### Host com IP atualizado
```
[2026-05-05 11:35:42] USUARIO=hugodeolindo IP=10.96.32.57 TIPO=Host ACAO=ATUALIZOU OBJETO=SRVIMG | DETALHE: host.description => "Equipe PACS IP Novo: 10.33.42.5 | ERA: IP Antigo: 10.33.42.8
```

### Script executado manualmente
```
[2026-04-30 15:36:32] USUARIO=hugo.deolindo IP=10.96.32.57 TIPO=Script ACAO=EXECUTOU OBJETO=dcsaansrvfluigpf | DETALHE: script.command => ADICIONOU: "ping -c 3 10.96.128.116...,"script.output => ADICIONOU: "3 packets transmitted, 0 received, 100% packet loss
```

### Janela de manutenção criada
```
[2026-02-13 10:31:09] USUARIO=werickvl IP=10.96.40.149 TIPO=Manutenção ACAO=CRIOU OBJETO=DCSAANSRVPHAPP3 - Protheus aplicação.. | DETALHE: maintenance.name => ADICIONOU: "DCSAANSRVPHAPP3 - Protheus aplicação..,"maintenance.description => ADICIONOU: "Realizando Gmud para melhoria da aplicação
```
