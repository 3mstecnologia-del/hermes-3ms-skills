# OLT G08 — MIBs SNMP privadas

Base enterprise Intelbras: `1.3.6.1.4.1.13464`. System OID G08: `1.3.6.1.4.1.13464.1.10.7.1`.

## Monitoramento geral do sistema

| Descrição | OID | Tipo |
|-----------|-----|------|
| Utilização CPU (%) | 1.3.6.1.4.1.13464.1.14.2.1.3.1.0 | INT |
| Utilização memória (%) | 1.3.6.1.4.1.13464.1.14.2.1.3.2.0 | INT |
| Temperatura chipset Switch (°C) | 1.3.6.1.4.1.13464.1.14.2.1.3.3.0 | INT |
| Temperatura chipset GPON (°C) | 1.3.6.1.4.1.13464.1.14.2.1.3.4.0 | INT |
| Nome imagem ONT carregada | 1.3.6.1.4.1.13464.1.14.2.1.3.5.0 | String |
| Tamanho imagem ONT | 1.3.6.1.4.1.13464.1.14.2.1.3.6.0 | INT |

## Utilização de portas

Tabela indexada por slot/porta:

| Descrição | OID suffix |
|-----------|------------|
| Índice slot | .1.3.6.1.4.1.13464.1.14.2.3.5.1.1 |
| Índice porta | .1.3.6.1.4.1.13464.1.14.2.3.5.1.2 |
| Taxa Mbps TX | .1.3.6.1.4.1.13464.1.14.2.3.5.1.3 |
| Taxa Mbps RX | .1.3.6.1.4.1.13464.1.14.2.3.5.1.4 |
| Taxa % TX | .1.3.6.1.4.1.13464.1.14.2.3.5.1.5 |
| Taxa % RX | .1.3.6.1.4.1.13464.1.14.2.3.5.1.6 |
| Taxa pps TX | .1.3.6.1.4.1.13464.1.14.2.3.5.1.7 |
| Taxa pps RX | .1.3.6.1.4.1.13464.1.14.2.3.5.1.8 |

## SFP

| Descrição | OID suffix |
|-----------|------------|
| Índice porta | .1.3.6.1.4.1.13464.1.14.2.3.3.1.2 |
| Tipo transceiver | .1.3.6.1.4.1.13464.1.14.2.3.3.1.3 |
| Número série | .1.3.6.1.4.1.13464.1.14.2.3.3.1.9 |
| Temperatura | .1.3.6.1.4.1.13464.1.14.2.3.3.1.12 |
| Potência RX (dBm) | .1.3.6.1.4.1.13464.1.14.2.3.3.1.17 |
| Potência TX (dBm) | .1.3.6.1.4.1.13464.1.14.2.3.3.1.20 |
| Classe (1=B+, 2=C+) | .1.3.6.1.4.1.13464.1.14.2.3.3.1.26 |

## ONT — descoberta

| Descrição | OID suffix |
|-----------|------------|
| Índice porta | .1.3.6.1.4.1.13464.1.14.2.3.1.1.2 |
| Índice ONU | .1.3.6.1.4.1.13464.1.14.2.3.1.1.3 |
| Serial | .1.3.6.1.4.1.13464.1.14.2.3.1.1.4 |
| Vendor ID | .1.3.6.1.4.1.13464.1.14.2.3.1.1.8 |
| Device ID | .1.3.6.1.4.1.13464.1.14.2.3.1.1.12 |

## ONT — informações básicas

| Descrição | OID suffix |
|-----------|------------|
| Estado operacional (1=online, 0=offline) | .1.3.6.1.4.1.13464.1.14.2.4.1.1.1.6 |
| Distância | .1.3.6.1.4.1.13464.1.14.2.4.1.1.1.7 |
| Serial | .1.3.6.1.4.1.13464.1.14.2.4.1.1.1.8 |
| Tipo ONU | .1.3.6.1.4.1.13464.1.14.2.4.1.1.1.5 |

## ONT — óptica

| Descrição | OID suffix |
|-----------|------------|
| Potência RX ONT (dBm) | .1.3.6.1.4.1.13464.1.14.2.4.1.9.1.5 |
| Potência TX ONT (dBm) | .1.3.6.1.4.1.13464.1.14.2.4.1.9.1.6 |
| Temperatura ONT | .1.3.6.1.4.1.13464.1.14.2.4.1.9.1.8 |
| Potência RX OLT (dBm) | .1.3.6.1.4.1.13464.1.14.2.4.1.9.1.11 |
| Potência TX OLT (dBm) | .1.3.6.1.4.1.13464.1.14.2.4.1.9.1.12 |

## ONT — portas ethernet

| Descrição | OID suffix |
|-----------|------------|
| Estado admin (0=hab, 1=des) | .1.3.6.1.4.1.13464.1.14.2.4.2.1.1.5 |
| Estado conexão | .1.3.6.1.4.1.13464.1.14.2.4.2.1.1.6 |
| Velocidade | .1.3.6.1.4.1.13464.1.14.2.4.2.1.1.7 |

## Porta alarme (dry contact)

| OID | Valor |
|-----|-------|
| 1.3.6.1.4.1.13464.1.14.2.5.6.11.0 | Par de pinos que gerou alarme (1-8) |
| 1.3.6.1.4.1.13464.1.14.2.5.6.12.0 | 1=aberto→fechado, 0=fechado→aberto |

## Template Zabbix — itens sugeridos

- ICMP ping + SNMP availability
- CPU: `1.3.6.1.4.1.13464.1.14.2.1.3.1.0`
- Memória: `1.3.6.1.4.1.13464.1.14.2.1.3.2.0`
- Temperatura switch/GPON: `.1.3.3.0` / `.1.3.4.0`
- Discovery ONT por tabela `.1.3.6.1.4.1.13464.1.14.2.4.1.1.1.6`
- Trigger ONT offline quando valor = 0
- Potência RX ONT abaixo de -28 ou acima de -8 dBm (ajustar por política NOC)
