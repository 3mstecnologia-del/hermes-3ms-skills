# WAN failover

Cenário: duas (ou mais) saídas; rota primária e secundária; retorno quando a primária sara.

Não pressupor um probe público fixo. Usar alvos do **ambiente**: `<PROBE_A>`, `<PROBE_B>` (DNS interno, IP do provedor, monitor acordado).

## Read-only

```rsc
/ip address print
/ip route print where dst-address=0.0.0.0/0
/ip firewall nat print where chain=srcnat
/ip dhcp-client print
```

## Padrão recursivo (conceitual)

1. Rota /32 (ou host) até `<PROBE_A>` via gateway WAN1, `scope`/`target-scope` alinhados.
2. Default `distance=1` com `gateway=<PROBE_A>` (recursivo) e `check-gateway=ping` **ou** check no gateway WAN — conforme desenho validado no firmware.
3. Default `distance=2` via WAN2.

A combinação exata de `scope` e `target-scope` **deve ser lida no export atual** e na documentação da versão. Não copiar números mágicos de tutoriais sem conferir.

## Health checks

`check-gateway=ping` ou `arp` na rota. Confirmar que o alvo responde ICMP/ARP a partir da WAN correta (policy routing pode distorcer o teste).

## NAT

Cada WAN normalmente tem `srcnat`/`masquerade` `out-interface=<WAN_N>`. Failover sem NAT na WAN2 = tráfego sai com IP errado.

## DNS

Se o resolver padrão some com a WAN1, clientes quebram mesmo com rota. Verificar `/ip dns` e DHCP options.

## Retorno automático

Com recursive + distance, a rota primária volta quando o probe sara. Validar que não há flap (histerese): probes instáveis geram oscilação — considerar timeouts do firmware.

## Troubleshooting

| Sintoma | Verificar |
|---------|-----------|
| Não falha para WAN2 | Probe ainda responde na WAN1; distance; check-gateway |
| Não volta para WAN1 | Rota /32 residual; scope; NAT |
| Ping ok, apps não | DNS, FastTrack, firewall |
| Assimetria | Policy routing / mangle PCC esquecido |

## Alto impacto

Trocar default route e NAT de borda exige confirmação. Safe Mode recomendado em sessão remota.

## Rollback

Reativar rotas anteriores (`enable` / distances originais) a partir do backup. Sem reset-configuration.
