# Routing (RouterOS)

## Read-only

```rsc
/ip address print
/ip route print
/ip route print detail
/ip arp print
```

RouterOS 7 também:

```rsc
/routing/route print
/routing/table print
```

Se `/routing/route` não existir, o equipamento provavelmente é v6 — usar `/ip route`.

## Tipos

| Tipo | Origem típica |
|------|----------------|
| connected | Endereço na interface |
| static | `/ip route add` |
| default | `dst-address=0.0.0.0/0` |
| dynamic | DHCP, PPP, protocolos |

## Parâmetros estáticos importantes

| Campo | Função |
|-------|--------|
| `dst-address` | Prefixo de destino |
| `gateway` | Next-hop ou interface |
| `distance` | Preferência (menor vence) |
| `scope` / `target-scope` | Recursão de next-hop (failover) |
| `check-gateway` | `ping` ou `arp` — saúde do gateway |
| `routing-mark` / `routing-table` | Policy routing (v7: tabela FIB declarada) |

## Recursive routing

Usado em failover: rota default via next-hop que só é alcançável se uma rota /32 (probe) estiver ativa. Ver [wan-failover.md](wan-failover.md). Não copiar distâncias sem entender a tabela atual.

## ECMP

Múltiplas rotas com mesma `dst-address` e `distance` — balanceamento. Confirmar se o firmware aplica per-connection ou per-packet; testar antes de produção.

## Policy routing

1. Marcar conexão/pacote (mangle) **ou** usar routing table.
2. Em v7: `/routing/table add name=<TABLE> fib` **antes** das rotas da tabela.
3. Rotas com `routing-table=<TABLE>` (v7) ou `routing-mark=` (verificar versão).

Não misturar nomes de tabela v7 com marks v6 sem inspecionar `export`.

## Default route

Alterar `0.0.0.0/0` é alto impacto. Confirmar: qual WAN deve sair, NAT correspondente, e se a sessão de gestão usa essa rota.

## Validação

```rsc
/ip route print where dst-address=0.0.0.0/0
```

Ping/traceroute a partir do roteador (`/tool ping`, `/tool traceroute`) para um alvo **acordado no ambiente** — não exigir um resolvedor público específico.

## Rollback

Remover ou `disable` a rota adicionada; restaurar `distance`/`gateway` anteriores a partir do export `pre-change`. Nunca reset de fábrica.
