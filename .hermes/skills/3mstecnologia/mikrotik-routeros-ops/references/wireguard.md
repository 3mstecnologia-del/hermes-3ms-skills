# WireGuard no RouterOS

Disponível em **RouterOS 7** (`/interface wireguard`). Em RouterOS 6, não oferecer esta árvore.

Nunca exibir **private key** em relatórios. Placeholders:

`<WG_PRIVATE_KEY>` `<WG_PUBLIC_KEY>` `<REMOTE_PUBLIC_KEY>` `<REMOTE_ENDPOINT>` `<WG_PORT>` `<WG_LOCAL_IP>` `<REMOTE_SUBNET>` `<WG_IFACE>`

## Conceitos

| Elemento | Papel |
|----------|--------|
| interface | Túnel L3 (`/interface wireguard`) |
| private/public key | Par da interface local; só a **pública** é compartilhada |
| peer | Outra ponta (`/interface wireguard peers`) |
| endpoint | Host:porta UDP do peer (pode ser dinâmico) |
| endpoint-port / listen-port | UDP; `listen-port` local = `<WG_PORT>` |
| allowed-address | Prefixos **permitidos no túnel** (criptografia + roteamento WG) |
| persistent-keepalive | Keepalive UDP; essencial se o peer (ou este lado) está atrás de NAT/CGNAT |
| routing | Rotas OS para `<REMOTE_SUBNET>` via interface WG |
| firewall | **input** UDP `<WG_PORT>`; **forward** entre WG e LAN |
| NAT | Só quando não há roteamento simétrico; evitar NAT no túnel se o objetivo é alcançar LANs privadas |

`allowed-address` deve incluir os prefixos que **entram e saem** pelo peer. Falta de prefixo = handshake possível e tráfego filtrado pelo WG.

## Diagnóstico (read-only)

```rsc
:put [/system resource get version]
/interface wireguard print
/interface wireguard peers print
/ip address print where interface=<WG_IFACE>
/ip route print where gateway=<WG_IFACE>
/ip firewall filter print where dst-port=<WG_PORT>
```

Handshake e contadores (omitir chaves privadas no relatório):

```rsc
/interface wireguard peers print
```

Campos úteis: `current-endpoint-address`, `last-handshake`, `rx`, `tx`. Público do peer: `public-key` (é a chave **pública** do remoto — ok reportar).

Chave pública **local**:

```rsc
:put [/interface wireguard get <WG_IFACE> public-key]
```

## Criação segura (esqueleto)

Não aplicar em produção sem IPs e portas do ambiente.

```rsc
/interface wireguard
add name=<WG_IFACE> listen-port=<WG_PORT> comment="mgmt-tunnel"

/ip address
add address=<WG_LOCAL_IP>/<WG_PREFIX_LEN> interface=<WG_IFACE>

/interface wireguard peers
add interface=<WG_IFACE> \
    public-key="<REMOTE_PUBLIC_KEY>" \
    endpoint="<REMOTE_ENDPOINT>:<WG_PORT>" \
    allowed-address=<REMOTE_SUBNET> \
    persistent-keepalive=25s
```

O RouterOS gera o par de chaves da interface ao criar. Extraia só `public-key` para o outro lado.

Firewall (ajustar `in-interface-list` / WAN real):

```rsc
/ip firewall filter
add chain=input action=accept protocol=udp dst-port=<WG_PORT> \
    comment="WireGuard" place-before=<N>
```

Forward LAN ↔ WG (exemplo; posicionar **antes** de drops):

```rsc
/ip firewall filter
add chain=forward action=accept in-interface=<WG_IFACE> out-interface-list=<LAN_LIST>
add chain=forward action=accept in-interface-list=<LAN_LIST> out-interface=<WG_IFACE>
```

Rota para redes remotas:

```rsc
/ip route
add dst-address=<REMOTE_SUBNET> gateway=<WG_IFACE>
```

Se o servidor central precisa alcançar várias LANs atrás deste MikroTik, cada prefixo entra em `allowed-address` no **peer do servidor** e em rotas no servidor. No MikroTik, `allowed-address` do peer central deve incluir o IP do túnel e prefixos do servidor (ex. rede de monitoramento).

## Site-to-site

Dois roteadores (ou servidor + MikroTik), IPs no túnel, rotas para LANs de cada lado, firewall nos dois sentidos. Ver [examples/wireguard-site-to-site.md](../examples/wireguard-site-to-site.md).

**Routing sem NAT:** next-hop = interface WG (ou IP do peer no túnel). NAT não é necessário se os dois lados têm rotas de retorno.

**NAT necessário quando:** um lado não pode instalar rotas (host único, policy do provedor) ou precisa esconder a LAN. Documentar o custo (assimetria, quebra de acesso a redes internas).

## Road-warrior

Peer móvel: `allowed-address` no servidor = IP do cliente no túnel (`<WG_CLIENT_IP>/32`) + opcionalmente LAN se split-tunnel inverso. No cliente, default ou rotas seletivas. Keepalive no **lado atrás de NAT**. Ver [examples/wireguard-road-warrior.md](../examples/wireguard-road-warrior.md).

## Servidor central ↔ MikroTik remoto

Padrão: concentrador (Linux/MikroTik/CHR) com `listen-port` público ou port-forward; MikroTik em site com NAT/CGNAT inicia o túnel (`endpoint` + `persistent-keepalive`). Redes privadas atrás do gateway são anunciadas por **rotas estáticas** no servidor (ou OSPF — [examples/ospf-over-wireguard.md](../examples/ospf-over-wireguard.md)).

Útil para monitoramento, automação, administração remota e coletores SNMP/Zabbix — sem NAT da LAN para a internet.

## Múltiplas redes atrás do peer

`allowed-address` aceita lista (vírgula). Cada prefixo também precisa de rota no lado que origina o tráfego. Esquecer a rota OS = handshake OK, ping falha.

## MTU

Túnel UDP + overhead. Sintomas: ping curto ok, TCP/HTTPS falha ou stall. Ajustar `mtu` na interface WG e/ou MSS clamp em mangle — **validar valores no equipamento**; não inventar um MTU universal.

```rsc
/interface wireguard print
```

## Troubleshooting

### A) Sem handshake (`last-handshake` vazio / antigo demais)

- `endpoint` e DNS resolvem?
- UDP `<WG_PORT>` chega? (firewall **input** no listener; ACL no provedor)
- `listen-port` correto nos dois lados
- `public-key` trocada (chave do **outro** lado no peer)
- NAT upstream / CGNAT: keepalive no lado sem IP público
- Relógio do sistema (handshake usa tempo; NTP ajuda operação, mas WG não é TLS)

### B) Handshake presente, sem tráfego

- `allowed-address` incompleto
- IP da interface WG ausente ou subnet errada
- Falta `/ip route` para o prefixo remoto
- Firewall **forward** (não só input)
- NAT mascarando o túnel indevidamente

### C) Tráfego só em um sentido

- Rota de **retorno** no outro lado
- `allowed-address` assimétrico
- Firewall só em uma chain
- NAT em um sentido

### D) Peer atrás de NAT/CGNAT

- `persistent-keepalive` no peer NAT (ex. 15–25s; validar)
- Endpoint dinâmico: o lado público vê `current-endpoint-address` mudar
- CGNAT: o listener deve ser o lado com mapeamento estável ou o servidor central

### E) Handshake antigo / intermitente

- WAN oscilando, DDNS do endpoint, firewall stateful, NAT mapping expirando, keepalive insuficiente, CPU/watchdog

## Validação pós-config

1. Handshake recente no peer.
2. Ping `<WG_REMOTE_TUNNEL_IP>`.
3. Ping a um host na `<REMOTE_SUBNET>` (se aplicável).
4. Contadores `rx`/`tx` incrementando nos dois sentidos.
5. Confirmar que gestão (SSH) não foi cortada.

## Rollback não destrutivo

```rsc
/interface wireguard peers remove [find where interface=<WG_IFACE> public-key="<REMOTE_PUBLIC_KEY>"]
/ip route remove [find where dst-address=<REMOTE_SUBNET> gateway=<WG_IFACE>]
/ip address remove [find where interface=<WG_IFACE>]
/interface wireguard remove [find where name=<WG_IFACE>]
```

Remover também a regra de firewall UDP adicionada (pelo `comment=`). Não usar reset-configuration.
