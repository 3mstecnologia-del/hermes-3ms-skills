# WireGuard no RouterOS

Disponível em **RouterOS 7** (`/interface wireguard`). Em RouterOS 6, não oferecer esta árvore.

Nunca exibir **private-key** nem **preshared-key** em relatórios. Placeholders:

`<WG_PRIVATE_KEY>` `<WG_PUBLIC_KEY>` `<REMOTE_PUBLIC_KEY>` `<REMOTE_ENDPOINT>` `<WG_PORT>` `<WG_LOCAL_IP>` `<REMOTE_SUBNET>` `<WG_IFACE>` `<WG_PREFIX_LEN>`

## Conceitos

| Elemento | Papel |
|----------|--------|
| interface | Túnel L3 (`/interface wireguard`) |
| private/public key | Par da interface local; só a **pública** é compartilhada |
| peer | Outra ponta (`/interface wireguard peers`) |
| endpoint-address | Host ou IP UDP do peer (pode ser dinâmico / vazio se o peer inicia) |
| endpoint-port | Porta UDP do peer (`<WG_PORT>` no remoto) |
| listen-port | Porta UDP local da interface |
| allowed-address | Seleção de peer + filtro criptográfico (não é a tabela de rotas) — ver abaixo |
| persistent-keepalive | Keepalive UDP; essencial se o peer (ou este lado) está atrás de NAT/CGNAT |
| routing | Rotas OS para `<REMOTE_SUBNET>` via interface WG |
| firewall | **input** UDP `<WG_PORT>`; **forward** entre WG e LAN |
| NAT | Só quando não há roteamento simétrico; evitar NAT no túnel se o objetivo é alcançar LANs privadas |

## allowed-address (não é rota)

No RouterOS, `allowed-address` no peer **não substitui** `/ip route` (nem `/ipv6 route`).

Ele faz duas coisas no **contexto da interface WireGuard**:

1. **Origem (entrada):** quais endereços/prefixos são aceitos como tráfego **vindo daquele peer** (decapsulado).
2. **Destino (saída):** quais destinos de tráfego **saindo pelo túnel** são associados **àquele peer** (qual chave pública encapsula o pacote).

Consequências:

- Sem o prefixo em `allowed-address`, o peer pode ter handshake e mesmo assim o tráfego ser descartado ou ir para o peer errado.
- Com o prefixo em `allowed-address` mas **sem rota** no RouterOS para esse destino via a interface WG, o pacote pode nem chegar ao WireGuard.
- **Peers da mesma interface não podem ter `allowed-address` sobrepostos.** Overlap = o RouterOS não consegue decidir o peer. Antes de `add`, listar peers existentes e comparar prefixos. Se houver interseção, **não criar** o peer; pedir revisão.

Não ensinar `allowed-address=0.0.0.0/0` como padrão. Full-tunnel só no cenário explícito (road-warrior), com os alertas de rota default, gestão, NAT, DNS e lockout.

Lista (vírgula) = vários prefixos **daquele** peer. Cada prefixo de LAN remota que o roteador deve encaminhar ainda precisa de rota OS.

## Diagnóstico (read-only) — sem secrets

Não usar `print detail` na **interface** WireGuard (expõe `private-key`). Não usar `export show-sensitive`. Em peers, não reportar `preshared-key` (redigir se aparecer).

```rsc
:put [/system resource get version]
/interface wireguard print
:put [/interface wireguard get <WG_IFACE> public-key]
/interface wireguard peers print
/ip address print where interface=<WG_IFACE>
/ip route print where gateway=<WG_IFACE>
/ip firewall filter print where dst-port=<WG_PORT>
```

Campos úteis nos peers: `public-key`, `endpoint-address`, `endpoint-port`, `current-endpoint-address`, `allowed-address`, `last-handshake`, `rx`, `tx`. **Omitir** `private-key` e `preshared-key`.

## Criação segura (esqueleto)

Não aplicar em produção sem IPs e portas do ambiente.

Cada `add`/`set` abaixo é **uma mutação**. Em SSH não interativo: uma por sessão, evidência (exit/stdout/stderr), depois `get` do objeto — ver [safe-ssh-mutation.md](safe-ssh-mutation.md). Não colar o bloco inteiro como um único comando remoto.

```rsc
/interface wireguard
add name=<WG_IFACE> listen-port=<WG_PORT> comment="mgmt-tunnel"

/ip address
add address=<WG_LOCAL_IP>/<WG_PREFIX_LEN> interface=<WG_IFACE>

/interface wireguard peers
add interface=<WG_IFACE> \
    public-key="<REMOTE_PUBLIC_KEY>" \
    endpoint-address=<REMOTE_ENDPOINT> \
    endpoint-port=<WG_PORT> \
    allowed-address=<REMOTE_SUBNET> \
    persistent-keepalive=25s
```

Antes do `add`: `/interface wireguard peers print where interface=<WG_IFACE>` e garantir que `<REMOTE_SUBNET>` **não intersecta** `allowed-address` de outro peer na mesma interface.

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

Padrão: concentrador (Linux/MikroTik/CHR) com `listen-port` público ou port-forward; MikroTik em site com NAT/CGNAT inicia o túnel (`endpoint-address` + `endpoint-port` + `persistent-keepalive`). Redes privadas atrás do gateway são anunciadas por **rotas estáticas** no servidor (ou OSPF — [examples/ospf-over-wireguard.md](../examples/ospf-over-wireguard.md)).

Útil para monitoramento, automação, administração remota e coletores SNMP/Zabbix — sem NAT da LAN para a internet.

## Múltiplas redes atrás do peer

`allowed-address` aceita lista (vírgula) **no mesmo peer**. Cada prefixo ainda precisa de rota no RouterOS se o tráfego for encaminhado (não originado só no próprio roteador). Esquecer a rota OS = handshake OK, ping à LAN falha.

Não sobrepor esses prefixos com outro peer da mesma interface.

## MTU

Túnel UDP + overhead. Sintomas: ping curto ok, TCP/HTTPS falha ou stall. Ajustar `mtu` na interface WG e/ou MSS clamp em mangle — **validar valores no equipamento**; não inventar um MTU universal.

```rsc
/interface wireguard print
```

## Troubleshooting

### A) Sem handshake (`last-handshake` vazio / antigo demais)

- `endpoint-address` / DNS resolvem?
- UDP `<WG_PORT>` chega? (firewall **input** no listener; ACL no provedor)
- `listen-port` local vs `endpoint-port` do peer
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

- WAN oscilando, DDNS de `endpoint-address`, firewall stateful, NAT mapping expirando, keepalive insuficiente, CPU/watchdog

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
