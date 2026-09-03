# Changelog — mikrotik-routeros-ops

Formato baseado em [Semantic Versioning](https://semver.org/).

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
