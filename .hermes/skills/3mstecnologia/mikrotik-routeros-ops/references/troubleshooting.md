# Troubleshooting MikroTik (visão geral)

Fluxo: identificar versão → health → camada (L1/L2/L3/serviço) → firewall/NAT → rota → logs.

## Health

```rsc
/system resource print
/system health print
/log print where topics~"error|critical|warning"
```

CPU alta: `/tool profile` se existir na versão. Temperatura/voltagem em `health` quando o hardware expõe.

## Sem conectividade

1. Interface `running`? `/interface print`
2. Endereço/máscara? `/ip address print`
3. Rota? `/ip route print`
4. ARP? `/ip arp print`
5. Firewall stats nas regras drop
6. NAT

## Gestão inacessível

Não recomendar reset. Caminhos: console serial, Winbox MAC na L2, porta de backup, Safe Mode se a sessão ainda existe. `reset-configuration` só com confirmação explícita e acesso físico/plano de restore.

## VPN

WireGuard: [wireguard.md](wireguard.md). Outros túneis: inspecionar interface, política, e se FastTrack/NAT interferem.

## Roteamento dinâmico

OSPF neighbor down: L2/túnel, protocol 89, router-id duplicado, area mismatch. BGP: [bgp.md](bgp.md).

## PPPoE cliente não navega

```rsc
/ppp active print
/ip route print
/ip firewall nat print
```

Não dump de `/ppp secret`.

## Relatório

Usar o template do [SKILL.md](../SKILL.md). Incluir versão RouterOS em toda análise.
