# Firewall (RouterOS)

Chains principais: **input**, **forward**, **output**. Tabelas adicionais: **raw**, **mangle**, **nat** (srcnat/dstnat).

## Identificar antes de inserir

```rsc
/ip firewall filter print
/ip firewall nat print
/ip firewall mangle print
/ip firewall raw print
/ip firewall connection print count-only
/interface list member print
```

A **ordem** importa. Anotar números (`print`) e usar `place-before=` (ou inserir na posição correta no Winbox) para não cair no default drop depois da regra errada.

Nunca adicionar `drop` em `input` sem regra prévia que permita o retorno da **sessão de gerenciamento** (SSH/Winbox/API) — risco de lockout. Preferir Safe Mode em mudanças remotas.

## Conceitos

| Conceito | Uso |
|----------|-----|
| connection tracking | Estado da conexão (new, established, related, invalid, untracked) |
| established/related | Aceitar retorno de sessões já permitidas |
| invalid | Descartar estados inconsistentes |
| FastTrack | Acelera established/related; posicionar após accept de established |
| address-list | Grupos de IPs para match |
| interface-list | WAN/LAN/MGMT — preferir listas a nomes soltos de ether |

## Diagnóstico

```rsc
/ip firewall filter print stats
/ip firewall nat print stats
```

Pacotes incrementando em `drop` inesperado: correlacionar `in-interface`, `src-address`, `dst-port`.

## Inserção segura (padrão)

1. Listar regras e interface-lists.
2. Planejar posição (`place-before=<N>`).
3. Safe Mode se a mudança puder cortar gestão.
4. Adicionar **accept** específico antes de qualquer drop novo.
5. Validar sessão de gestão ainda ativa.
6. Só então persistir.

## Alto impacto (confirmação)

- `/ip firewall filter remove` em massa
- disable da regra que aceita SSH/Winbox na WAN ou VPN
- `action=drop` no início de `input` sem exceções

## NAT

```rsc
/ip firewall nat print
```

src-nat/masquerade na WAN; dst-nat para publicação. Mudar NAT de gestão ou de VPN exige validar rota de retorno — ver [wireguard.md](wireguard.md) e [routing.md](routing.md).

## FastTrack vs VPN/mangle

Tráfego que precisa de mangle, IPsec ou às vezes forwarding especial **não** deve ser FastTracked cegamente. Se VPN ou policy routing falhar com FastTrack ativo, testar exclusão (regra accept sem fasttrack, ou `connection-mark`) — validar no firmware; não inventar matchers.

## IPv6

Se `/ipv6 firewall` existir, tratar como tabela **separada**. Não assumir que regras IPv4 cobrem IPv6.
