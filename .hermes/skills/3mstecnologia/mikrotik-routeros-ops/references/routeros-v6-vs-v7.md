# RouterOS 6 vs 7

Identificar sempre:

```rsc
:put [/system resource get version]
```

A sintaxe abaixo é a **árvore canônica conhecida**; se um comando falhar, use `?` no prompt e não force a outra major.

## Disponibilidade

| Recurso | RouterOS 6 | RouterOS 7 |
|---------|------------|------------|
| WireGuard | Ausente | `/interface wireguard` (desde ~7.1) |
| REST API JSON | Não usar como padrão | `/rest/` (7.1+) |
| Container | Ausente | `/container` (versões posteriores de v7) |
| IPv6 | Package em muitas instalações | Nativo |
| Routing tables | Marca via mangle (`routing-mark`) | Declarar `/routing/table` com `fib` antes de usar |
| BGP | `/routing bgp peer` | `/routing/bgp/template` + `connection` + `session` |
| BGP filters | `/routing filter` | `/routing/filter/rule` |
| OSPF instance/area | `/routing ospf ...` | `/routing/ospf/...` (paths com `/`) |
| OSPF em interface | `/routing ospf interface` | `/routing/ospf/interface-template` |
| NTP | `/system ntp client` | `/system/ntp/client` |
| Bridge VLAN | Frequentemente por porta | `/interface bridge vlan` (filtering centralizado) |

Slash em paths (`/routing/ospf/instance`) é estilo v7; v6 aceita espaço (`/routing ospf instance`). Em scripts, seguir o que o `print` do equipamento aceitar.

## FastTrack

Em v7, a regra `fasttrack-connection` deve restringir a `connection-state=established,related`. Aplicar FastTrack amplo demais em v7 é hipótese de comportamento diferente — validar no equipamento.

## BGP (não misturar)

**v6 — diagnóstico:**

```rsc
/routing bgp peer print status
/routing bgp advertisements print
```

**v7 — diagnóstico:**

```rsc
/routing/bgp/connection print
/routing/bgp/session print
/routing/bgp/advertisements print
```

Configuração v6 de `peer` **não** aplica em v7. Recriar com template + connection.

## OSPF

Ver [ospf.md](ospf.md). Redistribuição e “networks” mudaram de lugar entre majors — inspecionar `export` da instância antes de editar.

## Routing policy

v7: criar tabela antes de `routing-mark` / `routing-table=` nas rotas:

```rsc
/routing/table add name=<TABLE_NAME> fib
```

## WireGuard

Não oferecer `/interface wireguard` em RouterOS 6. Alternativas (IPsec, L2TP, etc.) estão fora do foco 0.1.0 desta skill.

## Em caso de dúvida

1. Confirmar major.
2. Tentar o comando da coluna correspondente.
3. Se falhar: reportar o erro literal e não “traduzir” automaticamente para a outra versão.
