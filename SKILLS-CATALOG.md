# Catálogo de Skills — 3MS Tecnologia

Repositório: **hermes-3ms-skills** · Namespace: **3mstecnologia**

| Skill | Versão | Status | Fabricante | Produto | Tecnologia | Firmware validado | Última validação | Descrição |
|-------|--------|--------|------------|---------|------------|-------------------|------------------|-----------|
| [`olt-intelbras-g08-ops`](.hermes/skills/3mstecnologia/olt-intelbras-g08-ops/SKILL.md) | 0.1.0 | DEV | Intelbras | OLT G08 | GPON | GPON Cassette V100R001* (manual) | Documentação (manual PDF) | Provisionamento ONT, deploy profiles, VLAN, óptica, SNMP, firmware, redundância PON |
| [`mikrotik-routeros-ops`](.hermes/skills/3mstecnologia/mikrotik-routeros-ops/SKILL.md) | 0.1.0 | DEV | MikroTik | RouterOS (RB/CCR/CRS/CHR/hAP) | RouterOS / Networking | ainda não homologado | Documentação (DEV) | Auditoria, firewall, routing, WireGuard, OSPF, diagnóstico BGP, VLAN/bridge, WAN failover, SNMP |

**Acionamento no Hermes:** `/skill olt-intelbras-g08-ops` · `/skill mikrotik-routeros-ops`

### Legenda de status

| Status | Significado |
|--------|-------------|
| DEV | Em desenvolvimento; não homologada por completo; pode mudar; não é configuração universalmente validada |
| LAB | Testada em laboratório ou hardware controlado |
| STABLE | Suficientemente homologada para uso operacional dentro do escopo documentado |
| DEPRECATED | Mantida somente por compatibilidade ou histórico |
