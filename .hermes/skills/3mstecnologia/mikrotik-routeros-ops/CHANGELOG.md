# Changelog — mikrotik-routeros-ops

Formato baseado em [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-09-03

### Status: DEV

Contrato obrigatório para mutações RouterOS via SSH não interativo (Addresses #1).

- Uma mutação por fronteira de evidência; capturar transporte, exit status, stdout e stderr
- Resultados: `applied`, `not-applied`, `failed-after-apply`, `mismatch`, `indeterminate`
- `print` compacto que omite atributo = `inconclusive`; leitura `get`/projeção antes de falhar ou rollback
- Sem rollback cego; sequência para em erro, divergência ou evidência incompleta
- Referência: `references/safe-ssh-mutation.md`
- Helper testável: `tests/safe_routeros_exec.py` (unittest, Docker ou `python3 -m unittest`)

## [0.1.1] — 2026-09-02

### Status: DEV

Correção de orientação WireGuard antes da primeira instalação no Hermes.

- Sintaxe de peer RouterOS 7: `endpoint-address` + `endpoint-port` (não `endpoint=host:port` como forma principal)
- `allowed-address` documentado como filtro/seleção de peer — **não** substitui `/ip route`; overlap na mesma interface é conflito
- Inspeção sem `print detail` na interface; omitir `private-key` e `preshared-key`
- `0.0.0.0/0` no cliente WG só em full-tunnel explícito, com alertas
- OSPF: `type=ptp` como valor documentado no ROS 7
- Teste 15: overlap de `allowed-address`

## [0.1.0] — 2026-09-02

### Status: DEV

Primeira implementação própria 3MS (não é cópia da skill externa de referência).

- Core operations: identificação, RouterOS 6 vs 7, read-first, backup/export, Safe Mode, relatório
- Firewall, routing, VLAN/bridge, WAN failover, SNMP
- WireGuard como capacidade de primeira classe (conceitos, site-to-site, road-warrior, troubleshooting)
- OSPF (v6/v7) e cenário OSPF sobre WireGuard
- BGP: diagnóstico seguro apenas
- Troubleshooting e testes textuais do agente

### Segurança deliberada

- Rollback **não** usa `/system reset-configuration`
- Sem communities SNMP, IPs de NMS ou dados de cliente
- Private keys WireGuard apenas como placeholders

### Pendente

- Homologação em equipamento real (LAB)
- BGP além de diagnóstico
- Confirmar no equipamento flags que o firmware possa divergir
