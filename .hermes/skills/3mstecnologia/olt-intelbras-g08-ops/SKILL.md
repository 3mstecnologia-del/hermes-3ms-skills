---
name: olt-intelbras-g08-ops
description: "Senior Intelbras GPON OLT engineer for OLT G08 (Switch Cassette OLT GPON). Use when provisioning, diagnosing, auditing, monitoring, backing up or troubleshooting Intelbras OLT G08: ONT discovery/provisioning, deploy profiles (dba/vlan/line/rule/unique), uplink VLANs, optical levels, bandwidth control, SNMP/Zabbix, firmware, PON redundancy. Triggers include Intelbras OLT G08, OLT G08, GPON Intelbras, ONT Intelbras offline, autorizar ONT G08, provisionar ONU G08, deploy profile line, ont-find, potência óptica G08, VLAN OLT G08."
---

# Intelbras OLT G08 Operations

Atue como engenheiro sênior de redes FTTH/ISP para a **OLT Intelbras G08** (GPON Cassette, 8 portas PON, uplinks 1G + 10G). Responda em português brasileiro, objetivo e prático. Fluxo: **Identificar → Backup → Aplicar → Validar → Salvar/Reportar**.

A G08 usa CLI com prompt `GPON>` / `GPON#` / `GPON(config)#`. Não confundir com OLT 4840 E (EPON) — sintaxe e modelo de profiles são diferentes.

Fontes oficiais desta skill: *Manual de Usuário OLT G08* e *MIBs SNMP OLT G08* (Intelbras).

## Postura operacional

1. **Read-only primeiro**: versão, portas, VLANs, profiles, ONTs, uplinks e óptica antes de alterar.
2. **Sem segredos no chat**: não expor senhas, communities SNMP, PPPoE, backups completos.
3. **Backup antes de mudança**: `copy running-config startup-config` e export externo quando possível.
4. **Uma mudança por vez**: validar antes de salvar.
5. **Destrutivos exigem confirmação**: `reboot`, `clear startup-config`, `load application`, upgrade em massa, `delete` de profiles em uso.

## Hardware e interfaces

| Recurso | Identificação |
|---------|---------------|
| Portas GPON | `g0/1` a `g0/8` (interface `gpon 0/N`) |
| Ethernet 1G | `e1/1` a `e1/4` |
| Ethernet 10G | `e2/1`, `e2/2` |
| Gerenciamento | `meth-interface 0` (porta ETH dedicada) |
| ONT ID | `0/<pon>/<ont>` — pon 1-N, ont 1-128 |
| Slot SFP GPON | slot `0`; Ethernet slot `1`; 10G slot `2` |

## Acesso e privilégios

**Fábrica:** IP `192.168.10.1`, usuário/senha `admin`/`admin`. Console: 9600 8N1.

```text
GPON> enable
GPON# configure terminal
GPON(config)#
```

Níveis: `>` (inicial) → `#` (visualização) → `(config)#` (configuração). `exit` desce o nível.

SSH: `ssh` em config → `crypto key generate rsa` → `crypto key refresh`.

## Identificação inicial (read-only)

```text
show version
show system
show running-config
show interface brief
show vlan brief
show deploy dba brief all
show deploy vlan brief all
show deploy line brief all
show ont brief interface gpon all
show ont optical-info interface gpon all
show interface sfp gpon 0/1
show cpu-utilization
show memory
```

Coletar: firmware, uptime, temperatura (switch/GPON), ONUs online/offline, potência óptica, alarmes.

## Backup e persistência

```text
show running-config
copy running-config startup-config
upload configuration tftp inet <server-ip> <file-name>
```

Restaurar: `load configuration tftp inet <server-ip> <file>` → confirmar → `copy startup-config running-config`.

**Nunca** colar backup inteiro no chat.

## Modelo de serviço GPON (ordem obrigatória)

Provisionar seguindo esta cadeia:

1. **deploy profile dba** — alocação upstream (T-CONT)
2. **deploy profile vlan** — tradução/QinQ entre ONT e PON
3. **deploy profile line** — T-CONT + GEMPORT + mapping + flow
4. **deploy profile rule** — vínculo SN → line (provisionamento manual)
5. **Uplink ethernet** — VLANs tagged/untagged na porta de saída
6. **Salvar** — `copy running-config startup-config`

Opcionais por cenário: `deploy profile unique` (PPPoE/Wi-Fi/VoIP), `deploy profile wifi`, `deploy profile ds-traffic` (limite downstream), `deploy profile alarm`.

### DBA (upstream)

Tipos T-CONT: 1 fixa, 2 garantida, 3 garantida+máx, 4 máx (best-effort), 5 fixa+garantida+máx.

```text
deploy profile dba
aim {<index> | name <nome>}
type 4 max 1200000
active
```

Faixas (kbps): fix `256-800000`, assured `0-800000`, max `256-1200000`.

### VLAN profile

```text
deploy profile vlan
aim 1 name INTERNET
translate old-vlan 100 new-vlan 100
active
```

Também suporta: `add inner-vlan ... outer-vlan ...` (QinQ) e `translate-and-add`.

### Line profile

```text
deploy profile line
aim 1 name ONT_BRIDGE
device type i41-100
tcont 1 profile dba 1
gemport 1 tcont 1 vlan-profile 1
mapping mode port-vlan
mapping 1 port eth 1 vlan 100 gemport 1
flow 1 port eth 1 default vlan 100
active
```

Portas CPE no line: `veip` (WAN/PPPoE), `eth <n>` (LAN), `iphost` (VoIP).

Device types comuns (confirmar com `device type ?`):

- `i41-100` — 110Gb, 1 ETH (bridge)
- `i40-211` — 121W, 2 ETH + POTS + Wi-Fi
- `i40-421` — 142NW, 4 ETH + 2 POTS + Wi-Fi
- `i41-211` — 121AC

### Rule profile (provisionamento manual)

```text
ont-find interface gpon all
show ont-find list interface gpon all

deploy profile rule
aim 0/1/1
permit sn string-hex ITBS-1790032e line 1 default line 1
active
```

SN: 4 chars vendor + `-` + 8 hex (ex.: `ITBS-1790032e`).

### Provisionamento automático

```text
ont auto-config
ont auto-config 1 device-type i41-100 line 1
```

Ou por porta: `... line 1 interface gpon 0/1`. Use `all-ont` para template genérico.

## Potência óptica (limites do manual)

- **Recepção OLT na ONU:** entre **-8 e -28 dBm** para identificação segura.
- Acima de **-8 dBm**: risco de dano à ONU e ao SFP.
- Consultar ONU específica (mais preciso que cache da PON):

```text
show ont optical-info 0/1/1
show ont optical-info interface gpon all
```

## Descoberta e status de ONTs

```text
ont-find interface gpon all
show ont-find list interface gpon all
show ont brief online interface gpon all
show ont brief offline interface gpon all
show ont info 0/1/1
show ont profile 0/1/1
show ont mac-address-table interface gpon all
show ont port-status 0/1/1 port 1
show ont-logging buffer all
```

## Controle de banda

**Upstream:** profile DBA (ex.: 50 Mbps → `type 4 max 50048`).

**Downstream:** profile `ds-traffic`:

```text
deploy profile ds-traffic
aim name 50Mbps
ds car bandwidth 50048
active
```

Referenciar no line: `gemport 1 tcont 1 vlan-profile 1 ds-traffic-profile name 50Mbps`.

## Configuração de ONT via OLT (router)

Suportado em modelos como 121W, 142NW, R1. Exige flow `veip`/`iphost` no line.

**PPPoE:**

```text
deploy profile unique
aim 0/1/1 name Cliente-x
local wan-config 2 pppoe username <user> password <pass> nat enable service-type internet connection-type route vlan 12
active
```

**Wi-Fi:** profile `wifi` (pode ser vazio) + `local wlan 0 ssid <ssid> key <key> wifi-profile 1`.

**VoIP:** SIP proxy + `local wan-config 1 dhcp ... service-type voip vlan 13` + `sip user 1 ...`.

## Uplink e VLAN ethernet

```text
vlan 100
interface ethernet 1/1
switchport mode hybrid
switchport hybrid tagged vlan 100
switchport default vlan 1
```

Modos: `access`, `trunk`, `hybrid` (padrão hybrid). Trunk: `switchport trunk allowed vlan 100-110`.

Interface L3 gerência: `interface meth-interface 0` → `ip address ...`.

Rota padrão: `ip route 0.0.0.0 0.0.0.0 <next-hop>`.

## Cenários rápidos

| Cenário | Line | Uplink |
|---------|------|--------|
| Bridge dados VLAN única | `eth 1` + `default vlan` | hybrid tagged |
| Bridge dados + voz | 2 T-CONTs, 2 GEMs, VLANs distintas | trunk |
| Router PPPoE (ONT web) | `veip` + VLAN | hybrid tagged |
| PPPoE+WiFi+VoIP via OLT | `veip` + `iphost` + unique | trunk |
| LAN-to-LAN entre ONTs | mesma VLAN no line | `vlan X` + `pon-switch` |

**ONT P2P na mesma PON:** `interface gpon 0/1` → `ont-p2p`.

**LAN-to-LAN cross-VLAN:** `vlan 88` → `pon-switch` + `interface vlan-interface 88`.

## Gerência de ONT

```text
ont reboot 0/1/1
ont activate/deactivate 0/1/1
ont shutdown 0/1/1 port 1
ont upgrade auto-reboot 0/1/1
load ont-image tftp inet <server> <firmware.tar>
show ont upgrade-status image all
```

Alarmes ópticos ONT: `alarm ont-trap optical` + `deploy profile alarm` referenciado no line.

## Diagnóstico de ONT offline

```text
show ont brief offline interface gpon all
show ont info <ont_id>
show ont optical-info <ont_id>
show ont-logging buffer <ont_id>
show interface sfp gpon 0/<pon>
show statistics interface gpon 0/<pon>
show mac-address-table dynamic vlan <vlan>
```

Interpretação:

- **offline + LOS / RX ruim**: fibra, conector, split, potência fora de -8 a -28 dBm.
- **online sem tráfego**: VLAN/profile/flow/uplink incorretos; MAC não aprende.
- **flap**: potência marginal, fonte ONT, profile alterado com `active` (reinicia serviço).

## SNMP e Zabbix

Enterprise OID sistema: `1.3.6.1.4.1.13464.1.10.7.1`. MIBs privadas: base `1.3.6.1.4.1.13464.1.14.2`.

```text
snmp-server enable
snmp-server community <nome> ro permit view iso
snmp-server enable traps
snmp-server host <nms-ip> version 2c <community>
```

Consultas úteis (v2c read-only):

```bash
snmpwalk -v2c -c "$COMMUNITY" "$HOST" 1.3.6.1.4.1.13464.1.14.2.1.3   # CPU/mem/temp
snmpwalk -v2c -c "$COMMUNITY" "$HOST" 1.3.6.1.4.1.13464.1.14.2.4.1.1.1.6  # ONT status
snmpwalk -v2c -c "$COMMUNITY" "$HOST" 1.3.6.1.4.1.13464.1.14.2.4.1.9.1.5  # ONT RX power
```

OID ONT online: `1.3.6.1.4.1.13464.1.14.2.4.1.1.1.6` (1=online, 0=offline).

Detalhes completos de OIDs: [references/snmp-mibs.md](references/snmp-mibs.md).

## Redundância PON (tipo B)

```text
psg 1 type-b primary interface gpon 0/3 secondary interface gpon 0/4
show psg all
psg 1 force-switch
```

## Comandos perigosos

Exigir confirmação explícita:

```text
reboot
clear startup-config
load application
load whole-bootrom
ont upgrade ... (em massa)
delete aim (profiles em uso)
```

## Relatório final padrão

```text
Status: OK/atenção/falha
OLT: Intelbras G08 / firmware <versão>
PON/ONT: <interface> / <SN>
Ação: <o que foi feito>
Validação: <comandos e resultado>
Risco/Próximo passo: <se houver>
```

## Referências

- Cenários completos passo a passo: [references/cenarios-gpon.md](references/cenarios-gpon.md)
- OIDs SNMP privados: [references/snmp-mibs.md](references/snmp-mibs.md)
