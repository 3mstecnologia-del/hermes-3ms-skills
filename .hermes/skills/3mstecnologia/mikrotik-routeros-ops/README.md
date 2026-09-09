# mikrotik-routeros-ops

Skill operacional para **MikroTik RouterOS** (v6 e v7): auditoria, diagnóstico, configuração segura, documentação e troubleshooting.

## O que é

Conjunto de procedimentos para o Hermes (e para operadores humanos) tratar roteadores e switches MikroTik como engenheiro de redes: **read-first**, backup antes de escrita, confirmação para ações de alto impacto, e relatórios sem secrets.

## Escopo

Inclui: health do sistema, interfaces, firewall, routing, WireGuard, OSPF, diagnóstico BGP, VLAN/bridge, WAN failover, SNMP para monitoramento, PPPoE (diagnóstico).

Não inclui: Netinstall, recuperação de senha com acesso físico, RMA de hardware, ou topologias de um cliente específico.

## Equipamentos

Qualquer dispositivo com RouterOS (RB, hAP, CCR, CRS, CHR, etc.). A skill não assume um modelo: identifica `/system resource` e `/system routerboard` no equipamento real.

## RouterOS suportado

| Major | Status nesta skill | Notas |
|-------|--------------------|--------|
| RouterOS 6 | DEV — comandos clássicos | Sem WireGuard nativo; BGP/OSPF na árvore antiga |
| RouterOS 7 | DEV — comandos novos | WireGuard ≥ 7.1; BGP connection/session; OSPF interface-template |

**Firmware homologado em laboratório:** ainda não. Versão **0.2.0 / DEV**.

A saída real do RouterOS e a [documentação oficial](https://help.mikrotik.com/) prevalecem sobre exemplos desta skill.

## Matriz de compatibilidade (áreas)

| Área | ROS 6 | ROS 7 | Homologado |
|------|-------|-------|------------|
| Identificação / backup | Sim | Sim | Não |
| Firewall filter/NAT/mangle | Sim | Sim (FastTrack exige `established,related`) | Não |
| Routing estático / failover | Sim | Sim (tabelas declaradas) | Não |
| WireGuard | Não | Sim (≥ 7.1) | Não |
| OSPF | Sim | Sim (sintaxe diferente) | Não |
| BGP | Diagnóstico | Diagnóstico (connection/session) | Não |
| VLAN / bridge | Sim | Preferir `bridge vlan` | Não |
| SNMP | Sim | Sim | Não |
| REST API | Não assumir | 7.1+ | Não |

## Áreas cobertas

- Mutação SSH atômica + evidência (uma mudança por sessão; pós-estado autoritativo)
- Core operations (identify, backup, Safe Mode)
- Firewall (input/forward/output, raw, mangle, NAT, FastTrack)
- Routing (connected, static, recursive, policy)
- WireGuard (site-to-site, road-warrior, troubleshooting de handshake)
- OSPF, incluindo cenário avançado sobre WireGuard
- BGP — diagnóstico seguro (não é referência completa)
- VLAN/bridge
- WAN failover
- SNMP / Zabbix (read-only, community placeholder)
- Troubleshooting

## Limitações

- Status **DEV**: não validado contra um firmware específico em laboratório
- BGP em 0.1.x é diagnóstico, não design de política de roteamento completo
- Não misturar sintaxe v6/v7
- Não usar `/system reset-configuration` como “rollback”
- SSH mutável: ver [references/safe-ssh-mutation.md](references/safe-ssh-mutation.md)

## Instalação

```bash
cp -a .hermes/skills/3mstecnologia/mikrotik-routeros-ops ~/.hermes/skills/3mstecnologia/
```

Ou copiar todo o namespace `3mstecnologia`. No Hermes: `/reload-skills`.

## Segurança

- Placeholders: `<HOST>`, `<USERNAME>`, `<PASSWORD>`, `<SNMP_COMMUNITY>`, `<WG_PRIVATE_KEY>`, `<REMOTE_PUBLIC_KEY>`
- Private keys WireGuard **nunca** em relatórios
- Confirmação explícita para reboot, reset, firmware, firewall em massa, gestão, VPN/routing crítico

Ver [CONTRIBUTING.md](../../../../CONTRIBUTING.md) e [SECURITY.md](../../../../SECURITY.md) na raiz do repositório.

## Contribuição

Novas áreas ou correções de sintaxe: atualizar `CHANGELOG.md`, `SKILLS-CATALOG.md` e marcar o que foi **confirmado** vs **hipótese**.

## Exemplos

- [examples/wireguard-site-to-site.md](examples/wireguard-site-to-site.md) — servidor de gestão ↔ gateway remoto e LANs privadas
- [examples/wireguard-road-warrior.md](examples/wireguard-road-warrior.md)
- [examples/ospf-over-wireguard.md](examples/ospf-over-wireguard.md)

## Roadmap

- Homologar o contrato SSH atômico em RouterOS 7.x real (Madalena Labs → LAB)
- Homologar em RouterOS 7.x e 6.x reais (promover a LAB)
- Ampliar BGP (filters, communities) após validação
- Templates Docker para testes de MCP futuros (fora desta skill)
