# Exemplo avançado: OSPF sobre WireGuard

WireGuard fornece um **enlace L3** (interface com IP). OSPF pode formar adjacência **por essa interface** quando a arquitetura justificar (vários sites, prefixos que mudam, convergência). Para um único servidor de gestão e poucas LANs estáticas, **rotas estáticas costumam ser mais simples e previsíveis** — ver [wireguard-site-to-site.md](wireguard-site-to-site.md).

Não aplicar números de produção. Identificar RouterOS 6 vs 7: **OSPF sobre WG só existe se WG existir (v7)**.

## Por que pode funcionar

- WG = point-to-point típico (dois IPs no /30 ou /31 ou /24 de underlay).
- OSPF hello na interface `wg-*`.
- Prefixos das LANs entram como connected/stub ou via `network`/`interface-template`.

## Riscos

- Anunciar default ou tabelas inteiras para o túnel
- Redistribuição sem filtro
- MTU: OSPF e TCP podem falhar se o WG MTU for baixo demais
- Firewall bloqueando protocol 89 na interface WG
- `router-id` duplicado
- Network type broadcast em túnel (DR/BDR desnecessários)

## RouterOS 7 (esqueleto — validar no equipamento)

```rsc
/routing/ospf/instance
add name=ospf-mgmt router-id=<ROUTER_ID>

/routing/ospf/area
add name=backbone instance=ospf-mgmt area-id=0.0.0.0

/routing/ospf/interface-template
add interfaces=wg-mgmt area=backbone type=ptp
```

Nomes de propriedades (`type=ptp` vs `point-to-point`) **devem ser confirmados com `?`**. Se o comando falhar, não inventar o enum.

## RouterOS 6

Sem WireGuard nativo. OSPF sobre outro túnel L3 (GRE/IPsec etc.) é outro desenho — fora deste exemplo.

## Checklist antes de ligar OSPF no WG

1. Túnel WG estável (handshake, ping dos IPs do túnel).
2. MTU alinhado nos dois lados.
3. Firewall permite OSPF na interface WG.
4. `interface-template` / interface só nas ifaces pretendidas (não em WAN).
5. Filtros de redistribuição revisados.

## Validação

```rsc
/routing/ospf/neighbor print
/ip route print where ospf
```

Neighbor Full; prefixos esperados **somente**.

## Rollback

Disable da instance OSPF ou remoção do template da interface WG; túnel WG pode permanecer com rotas estáticas.
