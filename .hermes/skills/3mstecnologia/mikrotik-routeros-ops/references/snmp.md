# SNMP e monitoramento

## Inspeção

```rsc
/snmp print
/snmp community print
```

Não copiar communities existentes para o chat. Se precisar citar, use `<SNMP_COMMUNITY>` e descreva só `read-access` / `addresses`.

## Princípios

- Preferir **read-only**.
- Restringir `addresses=` ao coletor (`<NMS_IP>/32`).
- SNMPv3 (auth/priv) quando o firmware e o NMS suportarem — mais adequado que v2c em WAN.
- Não habilitar write-access para monitoramento.

## Enable (esqueleto v2c — placeholders)

```rsc
/snmp set enabled=yes contact="<CONTACT>" location="<LOCATION>"
/snmp community add name="<SNMP_COMMUNITY>" addresses=<NMS_IP>/32 \
    read-access=yes write-access=no
```

Se a community default `public` existir, **desabilitá-la ou restringi-la** — não deixar `0.0.0.0/0` em produção. Confirmar nomes de propriedades com `print` no equipamento.

## Validação externa

A partir do coletor (não precisa ser o host do agente):

```bash
snmpget -v2c -c "<SNMP_COMMUNITY>" -Oqv <HOST> 1.3.6.1.2.1.1.1.0
```

## Firewall

Permitir UDP 161 **somente** de `<NMS_IP>` em `input`.

## Zabbix

Itens típicos: ICMP, sysDescr, uptime, CPU/memória via MIBs padrão, tráfego `ifHCInOctets`/`ifHCOutOctets`. Templates específicos ficam no NMS, não nesta skill.

## Rollback

`/snmp set enabled=no` e/ou remover a community adicionada pelo `name=`. Não apagar communities sem saber se outro sistema depende delas.
