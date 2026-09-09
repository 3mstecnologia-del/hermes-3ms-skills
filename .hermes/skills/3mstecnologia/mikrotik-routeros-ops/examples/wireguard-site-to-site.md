# Exemplo: site-to-site — servidor de gestão ↔ gateway MikroTik

Padrão genérico (sem topologia de cliente):

```
Central Management Server
          |
       WireGuard
          |
    MikroTik Gateway
          |
   Remote Private LANs
```

O servidor precisa alcançar prefixos privados **atrás** do MikroTik (monitoramento, automação, administração, coletor tipo Zabbix). Tráfego de gestão **não** precisa sair NAT da LAN para a internet.

Pré-requisito: RouterOS 7 com WireGuard. Identificar versão antes.

## Papéis

| Lado | Função |
|------|--------|
| Servidor central | Listener UDP `<WG_PORT>` (ou DNAT no firewall da frente); rotas estáticas para `<REMOTE_LAN_A>`, `<REMOTE_LAN_B>`, … via túnel |
| MikroTik | Peer com `endpoint-address=<REMOTE_ENDPOINT>` e `endpoint-port=<WG_PORT>`; keepalive se estiver atrás de NAT; rotas para `<MGMT_NET>` via WG |

## Allowed-address (ideia)

Não confundir com rota: no RouterOS o `allowed-address` escolhe o peer e filtra origem/destino **no túnel**; a tabela `/ip route` continua obrigatória para encaminhar às LANs.

Prefixos de peers **na mesma interface** não podem se sobrepor.

**No servidor, peer = MikroTik:**

- IP do túnel do MikroTik (`<WG_REMOTE_IP>/32`)
- Cada LAN remota (`<REMOTE_LAN_A>`, …)

**No MikroTik, peer = servidor:**

- IP do túnel do servidor
- Prefixo(s) de gestão/monitoramento (`<MGMT_NET>`)

Assimétricos = um lado encapsula e o outro descarta.

## MikroTik (esqueleto)

Em SSH não interativo, cada `add` é uma mutação com validação própria ([safe-ssh-mutation.md](../references/safe-ssh-mutation.md)). O bloco abaixo é a **lista planejada**, não um único comando agregado.

```rsc
/interface wireguard
add name=wg-mgmt listen-port=<WG_PORT>

/ip address
add address=<WG_LOCAL_IP>/<WG_PREFIX_LEN> interface=wg-mgmt

/interface wireguard peers
add interface=wg-mgmt \
    public-key="<REMOTE_PUBLIC_KEY>" \
    endpoint-address=<REMOTE_ENDPOINT> \
    endpoint-port=<WG_PORT> \
    allowed-address=<MGMT_NET> \
    persistent-keepalive=25s

/ip route
add dst-address=<MGMT_NET> gateway=wg-mgmt
```

Se o servidor só precisa iniciar sessões **para** as LANs, o MikroTik ainda precisa de rota de **retorno** para `<MGMT_NET>` (senão o reply não volta).

Firewall: accept UDP `<WG_PORT>` em `input`; forward entre `wg-mgmt` e bridge/LAN.

**Não** usar masquerade na interface WG se o objetivo é roteamento transparente.

## Servidor (conceitual)

Config WireGuard do SO (`wg0`): `Address = <WG_SERVER_IP>/<WG_PREFIX_LEN>`, `ListenPort = <WG_PORT>`, peer com `AllowedIPs` = túnel MikroTik + LANs remotas. Rotas OS iguais aos AllowedIPs (muitos sistemas instalam via `AllowedIPs`).

Trocar apenas **chaves públicas**. Private keys ficam em cada caixa.

## NAT/CGNAT no site remoto

MikroTik inicia o túnel (`endpoint-address` + `endpoint-port` + `persistent-keepalive`). O servidor tem IP alcançável (público ou 1:1). Sem isso, handshake não sobe — ver troubleshooting A/D em [references/wireguard.md](../references/wireguard.md).

## Validação

1. Handshake no MikroTik e no servidor.
2. Ping IP do túnel.
3. Ping a um host de teste na LAN remota **a partir do servidor**.
4. SNMP/SSH do servidor para o alvo, se for o caso de uso.

## Rollback

Remover peer, rotas e interface `wg-mgmt` criados para este túnel; remover regra UDP correspondente. Sem reset-configuration.
