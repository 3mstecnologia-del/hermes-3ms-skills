# OSPF (RouterOS)

Identificar versão antes de qualquer `set`/`add`.

## Read-only

**RouterOS 6:**

```rsc
/routing ospf instance print
/routing ospf area print
/routing ospf interface print
/routing ospf neighbor print
/routing ospf route print
```

**RouterOS 7:**

```rsc
/routing/ospf/instance print
/routing/ospf/area print
/routing/ospf/interface-template print
/routing/ospf/neighbor print
/routing/ospf/lsa print
```

Se o path v7 falhar, não converter automaticamente para v6 sem confirmar a major.

## Peças

| Peça | Função |
|------|--------|
| instance | Processo OSPF; **router-id** estável (não deixar 0.0.0.0 em produção sem plano) |
| area | `0.0.0.0` backbone; áreas extras só com desenho |
| interface / interface-template | Onde OSPF hello corre (v7 usa templates) |
| neighbor | Adjacência |
| LSA / routes | Base de dados e rotas instaladas |
| redistribution | Injetar static/connected/BGP — risco de anunciar demais |
| filters | Prefixos permitidos (v7: routing filters) |

## Network type

Point-to-point vs broadcast muda DR/BDR e timers. Em **túneis** (WireGuard), point-to-point é o usual — confirmar no template/interface. Ver [examples/ospf-over-wireguard.md](../examples/ospf-over-wireguard.md).

## Firewall

OSPF usa IP protocol 89. Permitir entre vizinhos (input/forward conforme o salto). Túnel WG: garantir forward/input na interface WG.

## Redistribuição

Antes de `redistribute=`: listar o que o roteador já anuncia (`/ip route print`). Redistribuir `static` ou `connected` sem filtro pode vazar RFC1918 ou default para o AS errado.

## Alto impacto

Mudar `router-id`, area ID, ou remover interface OSPF em produção exige confirmação: pode reconvergir e cortar tráfego.

## Rollback

Reverter `export` da seção OSPF; `disable` da instance é mais seguro que apagar áreas em massa.
