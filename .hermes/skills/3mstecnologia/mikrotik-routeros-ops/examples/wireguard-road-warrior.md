# Exemplo: WireGuard road-warrior

Cliente móvel (notebook/telefone) ↔ MikroTik (ou CHR) que termina o túnel.

## Servidor (MikroTik ROS 7)

- Interface WG com `<WG_PORT>` publicado (firewall input UDP).
- Peer por cliente: `allowed-address=<WG_CLIENT_IP>/32`.
- Opcional: LAN do escritório em `allowed-address` se o cliente deve alcançá-la; aí o cliente também lista essa LAN em AllowedIPs.
- NAT: só se o cliente deve **sair à internet pelo MikroTik** (masquerade `out-interface-list=WAN` para tráfego vindo de `wg-*`). Split-tunnel = sem default pelo WG.

```rsc
/interface wireguard
add name=wg-rw listen-port=<WG_PORT>

/ip address
add address=<WG_SERVER_IP>/<WG_PREFIX_LEN> interface=wg-rw

/interface wireguard peers
add interface=wg-rw public-key="<REMOTE_PUBLIC_KEY>" \
    allowed-address=<WG_CLIENT_IP>/32 \
    comment="road-warrior"
```

Keepalive: no **cliente** se ele estiver em NAT.

Não colocar `0.0.0.0/0` no `allowed-address` do peer no MikroTik como padrão (conflitaria com outros peers e não substitui rotas). O usual é só `<WG_CLIENT_IP>/32`.

## Cliente (split-tunnel — padrão deste exemplo)

AllowedIPs no cliente = `<WG_SERVER_IP>/32` + LANs desejadas. Sem default pelo túnel.

## Cliente full-tunnel (exceção — não usar sem pedido explícito)

Só se o objetivo for **toda** a internet do cliente sair pelo MikroTik. No cliente, AllowedIPs pode incluir `0.0.0.0/0`. Isso **não** é o default desta skill.

Antes de aplicar, avisar e exigir confirmação:

- **Rota default** do cliente passa a ser o túnel — perda do caminho direto à WAN local.
- **Gestão:** SSH/Winbox para o MikroTik pelo IP público pode falhar se o return path mudar; planejar acesso pela LAN/WG ou console.
- **NAT:** o MikroTik precisa masquerade/srcnat do tráfego WG rumo à WAN.
- **DNS:** resolver do cliente deve continuar alcançável (ou ser o do roteador).
- **Policy routing / FastTrack:** podem interferir no tráfego encapsulado.
- Risco de **perda de conectividade** se o túnel cair e o default estiver no WG.

No MikroTik, mesmo em full-tunnel do cliente, o peer continua com `allowed-address=<WG_CLIENT_IP>/32` (origem do cliente), **não** `0.0.0.0/0` na mesma interface se houver outros peers.

## Validação

Handshake; ping `<WG_SERVER_IP>`; ping LAN se split-tunnel incluir. Não expor private-key/preshared-key.

## Rollback

`/interface wireguard peers remove [find comment="road-warrior"]` (ajuste o find). Não apagar a interface se outros peers dependem dela.
