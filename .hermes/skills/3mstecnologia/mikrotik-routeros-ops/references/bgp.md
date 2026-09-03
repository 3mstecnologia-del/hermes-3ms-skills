# BGP — diagnóstico seguro (0.1.0)

Esta versão **não** é um guia completo de desenho BGP. Foco: inspecionar sessões, anúncios, CPU e logs **sem** alterar política até haver confirmação e export.

## Separar v6 e v7

**RouterOS 6:**

```rsc
/routing bgp peer print status
/routing bgp peer print stats
/routing bgp advertisements print
/routing filter print
```

**RouterOS 7:**

```rsc
/routing/bgp/connection print
/routing/bgp/session print
/routing/bgp/template print
/routing/bgp/advertisements print
/routing/filter/rule print
```

Não usar `peer` v6 em v7. Não inventar nomes de campos de `session`.

## O que coletar

| Item | Por quê |
|------|---------|
| Estado da sessão/connection | Idle vs established |
| remote AS / address | Peer certo |
| advertisements | O que enviamos/recebemos |
| `/log print where topics~"bgp"` | Notificações, hold timer |
| `/system resource print` | CPU no control-plane |
| `/tool profile` (se disponível) | BGP/processo pesado |

Hold timer expirando com link ok: investigar CPU, flooding de updates, ou filtro quebrado — **read-only** primeiro.

## Routing filters

v7 usa `/routing/filter/rule` com linguagem própria. Não traduzir regras v6 (`/routing filter`) “no chute”. Exportar a chain e comparar com a documentação da versão.

## Templates (v7)

`/routing/bgp/template` concentra AS, router-id, address-families. Connection referencia o template. Diagnosticar os dois.

## Alteração

Qualquer `set` em peer/connection/template/filter em produção é **alto impacto** (confirmação explícita). Backup/export da seção routing antes.

## Rollback

Restaurar connection/peer a partir do export; não resetar o roteador.
