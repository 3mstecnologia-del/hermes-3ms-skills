# VLAN e bridge

## Read-only

```rsc
/interface bridge print
/interface bridge port print
/interface bridge host print
/interface vlan print
/interface bridge vlan print
```

v7 com VLAN filtering: a tabela `/interface bridge vlan` é o mapa tagged/untagged por bridge.

## Conceitos

- **Bridge** agrega portas L2.
- **PVID / untagged** vs **tagged** (802.1Q).
- VLAN filtering: se `vlan-filtering=yes`, tráfego que não casa a tabela é descartado — mudança pode isolar a gestão.

## Alteração segura

1. Identificar em qual porta está o uplink e a gestão (IP da bridge vs ether).
2. Não remover a VLAN de gestão da porta de uplink sem sessão alternativa (console, outra IP, Safe Mode).
3. Uma porta/VLAN por vez.
4. Validar `/interface bridge host print` e ping ao gateway.

## Alto impacto (confirmação)

- `vlan-filtering=yes` em bridge de produção sem tabela completa
- Remover porta de gestão da bridge
- Mudar PVID da porta de uplink

## RouterOS 6 vs 7

v6 ainda aparece configuração VLAN “espalhada” por porta. v7 incentiva `/interface bridge vlan`. Não converter automaticamente um `export` v6 para filtering v7 sem plano de migração.

## Rollback

Reverter `vlan-filtering`, members e PVID a partir do export `pre-change`.
