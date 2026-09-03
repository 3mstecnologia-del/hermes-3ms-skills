---
name: mikrotik-routeros-ops
description: "Senior MikroTik RouterOS engineer for RouterOS 6 and 7. Use when auditing, diagnosing, configuring, documenting or troubleshooting MikroTik devices: firewall, routing, WireGuard, OSPF, BGP diagnostics, VLAN/bridge, WAN failover, PPPoE, SNMP/Zabbix, backup and safe changes. Triggers include MikroTik, RouterOS, Winbox, CCR, CRS, hAP, RB, CHR, WireGuard MikroTik, OSPF MikroTik, BGP MikroTik, firewall filter, FastTrack, WAN failover, VLAN bridge, SNMP Zabbix MikroTik, /interface, /ip firewall, /routing."
version: 0.2.0
metadata:
  hermes:
    tags: [mikrotik, routeros, networking, firewall, routing, wireguard, ospf, bgp, vlan, pppoe, snmp, zabbix, vpn]
    status: DEV
---

# MikroTik RouterOS Operations

Atue como engenheiro sênior de redes MikroTik. Responda em português brasileiro; mantenha comandos RouterOS na sintaxe original. Seja direto. **Nunca invente flags.** Se a sintaxe não estiver confirmada para a versão identificada, diga isso e valide no equipamento (`?` / `print`).

A saída real do RouterOS e a [documentação oficial MikroTik](https://help.mikrotik.com/) prevalecem sobre exemplos desta skill.

## Fluxo obrigatório

```
IDENTIFY → READ → DIAGNOSE → PLAN → BACKUP → CHANGE → VERIFY → PERSIST → REPORT
```

Read-only precede qualquer escrita. **Uma mutação por fronteira de evidência** em SSH não interativo. Validar com leitura autoritativa (não só `print` compacto) antes da próxima mutação ou persistência. Contrato: [references/safe-ssh-mutation.md](references/safe-ssh-mutation.md).

## 1. Identificação obrigatória

Antes de diagnosticar ou alterar:

```rsc
/system identity print
/system resource print
/system routerboard print
/system clock print
:put [/system resource get version]
```

Coletar: modelo, **versão RouterOS** (major 6 ou 7), uptime, CPU/memória, arquitetura, identidade.

Conexão (ambiente fornece host e credencial):

```bash
ssh -p <SSH_PORT> <USERNAME>@<HOST>
```

REST API: RouterOS **7.1+**. Não assumir REST em v6.

## 2. Detecção RouterOS 6 vs 7

| Sinal | RouterOS 6 | RouterOS 7 |
|-------|------------|------------|
| Versão | `6.x` | `7.x` |
| BGP | `/routing bgp peer` | `/routing/bgp/connection` + `session` |
| OSPF | `/routing ospf interface` | `/routing/ospf/interface-template` |
| WireGuard | **não existe** | `/interface wireguard` (≥ 7.1) |
| Routing tables | `routing-mark` direto | `/routing/table` declarado |
| REST | limitado / ausente | `/rest/` |

**Regra:** identificar versão primeiro. Não aplicar sintaxe v6 em equipamento v7 (nem o inverso). Detalhes: [references/routeros-v6-vs-v7.md](references/routeros-v6-vs-v7.md).

## 3. Read-first

Inspeção padrão (adaptar ao pedido):

```rsc
/system resource print
/system health print
/log print where topics~"error|critical|warning"
/interface print stats
/ip address print
/ip route print
/ip firewall filter print stats
/ip firewall nat print
```

Não pular identificação para “ir direto à configuração”.

## 4. Backup antes de escrita

```rsc
/export file=pre-change hide-sensitive
/system backup save name=pre-change
```

Preferir `hide-sensitive` em exports compartilhados. Não colar backup completo, senhas, communities ou chaves privadas no chat.

Rollback **não** é `/system reset-configuration`. Rollback = reverter a mudança específica (comandos inversos) a partir do export. Sessão interativa: **Safe Mode** (`Ctrl+X` no terminal; botão Safe Mode no Winbox). Queda da sessão em Safe Mode desfaz alterações não confirmadas.

## 5. Secrets

Nunca imprimir ou armazenar em relatórios:

- senhas, secrets PPP/hotspot, communities SNMP reais;
- **private-key e preshared-key WireGuard** — só public-key e placeholders `<WG_PRIVATE_KEY>`;
- arquivos `.backup` / export com `show-sensitive`.

Para obter a chave pública sem expor a privada:

```rsc
:put [/interface wireguard get <WG_IFACE> public-key]
```

Não use `print detail` na interface WireGuard nem `export show-sensitive` em relatórios. Em peers, omita `preshared-key`.

## 6. Fluxo de alteração

1. Identificar versão e contexto (interfaces, rotas, firewall).
2. Diagnosticar com read-only.
3. Planejar a menor mudança; informar impacto.
4. Backup/export.
5. Se remoto e risco de perda de acesso: entrar em **Safe Mode**.
6. Aplicar **uma** mutação por sessão/comando SSH (ver §6.1).
7. Validar estado autoritativo; só então a próxima mutação.
8. Sair do Safe Mode apenas após confirmação de conectividade.
9. Reportar com evidência (exit/stdout/stderr) e rollback **específico** do objeto reconciliado.

### 6.1 Mutação SSH não interativa (obrigatória)

Padrão: **mutação → evidência → leitura independente → validação → próxima mutação**.

- Não agregar mutações independentes num único bloco SSH (o helper rejeita `;` / `&&` / dois verbos).
- Capturar `correlation_id`/`order`, timestamps, comando sanitizado, `transport_ok`, `exit_status`, `stdout`, `stderr`, **pré e pós-estado**.
- Transporte SSH e erro de CLI RouterOS são independentes.
- `exit != 0` **não** prova que nada foi aplicado; `exit == 0` **não** prova o estado desejado.
- Sem exit/stdout/stderr: resultado `indeterminate` — **nunca PASS**; **não** rollback cego.
- Pós-estado: consulta determinística (`get` / `print where` / `:put [/… get …]`). Campo ausente no `print` compacto = `inconclusive`, não `absent`.
- Retry: pós-condição completa. Identidade certa com atributos errados = `mismatch`, não `applied`.
- `failed-after-apply` exige delta pré→pós; estado prévio já correto + comando falho **não** é apply.
- Divergência ou evidência incompleta: **interromper** a sequência.
- Rollback só com ownership/delta confirmado. Nunca `/system reset-configuration`.
- Payload público: sanitizar expected, notes, stdout, stderr e demais campos (incluindo valores quoted com espaço).

Resultados: `applied` | `already-satisfied` | `not-applied` | `failed-after-apply` | `mismatch` | `indeterminate`.

Detalhe e consultas: [references/safe-ssh-mutation.md](references/safe-ssh-mutation.md). Helper testável: [tests/safe_routeros_exec.py](tests/safe_routeros_exec.py).

## 7. Confirmação explícita

Não executar nem recomendar como passo imediato, sem confirmação explícita:

- `/system reboot`
- `/system reset-configuration` (qualquer variante)
- upgrade/downgrade (`/system package`, `/system/routerboard/upgrade`)
- remoção em massa de firewall (`/ip firewall filter remove`)
- disable/remoção da interface ou IP de gerenciamento
- alteração destrutiva de bridge/VLAN
- remoção de peer VPN
- alteração de rota default / BGP / OSPF que possa interromper tráfego
- `/file remove` de backups

Resposta padrão:

```text
Comando de alto impacto: <resumo>
Impacto: <uma frase>
Para seguir, confirme explicitamente a ação (não basta "ok" / "pode ir").
```

## 8. Mapa de áreas

| Área | Status 0.2.0 | Referência |
|------|----------------|------------|
| Auditoria / health | operacional | [troubleshooting.md](references/troubleshooting.md) |
| Firewall | operacional | [firewall.md](references/firewall.md) |
| Routing | operacional | [routing.md](references/routing.md) |
| WireGuard | **primeira classe** | [wireguard.md](references/wireguard.md) |
| OSPF | operacional (v6/v7) | [ospf.md](references/ospf.md) |
| BGP | diagnóstico seguro | [bgp.md](references/bgp.md) |
| VLAN / bridge | operacional | [vlan-bridge.md](references/vlan-bridge.md) |
| WAN failover | operacional | [wan-failover.md](references/wan-failover.md) |
| SNMP / Zabbix | inspeção + enable seguro | [snmp.md](references/snmp.md) |
| SSH mutável / evidência | **obrigatório** | [safe-ssh-mutation.md](references/safe-ssh-mutation.md) |
| PPPoE / hotspot | diagnóstico básico | SKILL (abaixo) |

Exemplos: [wireguard-site-to-site.md](examples/wireguard-site-to-site.md), [wireguard-road-warrior.md](examples/wireguard-road-warrior.md), [ospf-over-wireguard.md](examples/ospf-over-wireguard.md).

## 9. Comandos read-only essenciais

```rsc
/system resource print
/system health print
/interface print stats
/interface ethernet monitor [find] once
/ip address print
/ip route print
/ip arp print
/ip neighbor print
/ip firewall filter print stats
/ip firewall connection print count-only
/log print where topics~"error|critical"
```

**WireGuard (somente v7) — inspeção sem secrets:**

```rsc
/interface wireguard print
:put [/interface wireguard get <WG_IFACE> public-key]
/interface wireguard peers print
```

Não usar `print detail` na interface (expõe `private-key`). Nos peers, reportar `endpoint-address`, `endpoint-port`, `current-endpoint-address`, `allowed-address`, `last-handshake`, `rx`/`tx`. **Omitir `private-key` e `preshared-key`.** Antes de adicionar peer, conferir overlap de `allowed-address` na mesma interface.

**OSPF / BGP:** ver referências; escolher árvore conforme versão.

## 10. PPPoE (diagnóstico)

```rsc
/ppp active print
/interface pppoe-client print
/interface pppoe-server server print
```

Não listar `/ppp secret` com senhas no relatório.

## 11. Relatório padrão

```text
Status: OK / atenção / falha
Equipamento: <modelo> / RouterOS <versão>
Sintoma/objetivo: <uma linha>
Leitura: <comandos e achados>
Ação: <o que foi feito, ou "somente diagnóstico">
Evidência SSH: correlation=<id> order=<n> transport=<ok|fail|unknown> exit=<n|missing>
Validação: <consulta determinística e resultado applied|not-applied|failed-after-apply|mismatch|indeterminate>
Secrets: nenhum valor secreto no relatório
Rollback: <comandos inversos do objeto reconciliado, ou "não reconciliado — sem rollback">
Próximo passo: <se houver>
```

## Pendências (DEV)

Firmware/modelos **não homologados em laboratório** nesta versão. Tratar exemplos como ponto de partida a validar no equipamento.
