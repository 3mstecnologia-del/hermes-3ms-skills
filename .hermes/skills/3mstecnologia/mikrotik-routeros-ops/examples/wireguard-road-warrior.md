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

## Cliente

AllowedIPs = `<WG_SERVER_IP>/32` + LANs desejadas, **ou** `0.0.0.0/0` se full-tunnel (implica NAT/firewall no MikroTik e rota default).

## Validação

Handshake; ping `<WG_SERVER_IP>`; ping LAN se split-tunnel incluir.

## Rollback

`/interface wireguard peers remove [find comment="road-warrior"]` (ajuste o find). Não apagar a interface se outros peers dependem dela.
