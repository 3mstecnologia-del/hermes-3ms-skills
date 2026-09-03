# OLT G08 — Cenários GPON (manual)

Ordem sempre: **dba → vlan → line → rule → uplink → save**.

## 1. ONT cliente PPPoE (142NW, config na WEB da ONT)

Uplink `ethernet 1/1` hybrid, VLAN 14 tagged. ONT em modo PPPoE via interface web.

```text
deploy profile vlan → aim 1 name VLAN-PPPoE → translate old-vlan 14 new-vlan 14 → active
deploy profile dba → aim 1 name NO-LIMIT → type 4 max 1200000 → active
deploy profile line → aim 1 name 142nw-PPPoE
  device type i40-421
  tcont 1 profile dba 1
  gemport 1 tcont 1 vlan-profile 1
  mapping mode port-vlan
  mapping 1 port veip vlan 14 gemport 1
  flow 1 port veip vlan 14 keep
  active
deploy profile rule → aim 0/1/1 → permit sn string-hex ITBS-xxxxxxxx line 1 default line 1 → active
vlan 14
interface ethernet 1/1 → switchport mode hybrid → switchport hybrid tagged vlan 14
copy running-config startup-config
```

## 2. ONU bridge dados + voz (110b, 2 VLANs na LAN)

VLAN 10 untagged (dados), VLAN 11 tagged (voz). Dois T-CONTs.

```text
deploy profile vlan → aim 1 name DADOS-VOZ
  translate old-vlan 10 new-vlan 10
  translate old-vlan 11 new-vlan 11 → active
deploy profile dba
  aim 1 name NO-LIMIT → type 4 max 1200000 → active
  aim 2 name VOIP → type 3 assured 512 max 2048 → active
deploy profile line → aim 1 name 110b-DADOS-VOZ
  device type i41-100
  tcont 1 profile dba 1
  tcont 2 profile dba 2
  gemport 1 tcont 1 vlan-profile 1
  gemport 2 tcont 2 vlan-profile 1
  mapping mode port-vlan
  mapping 1 port eth 1 vlan 10 gemport 1
  mapping 2 port eth 1 vlan 11 gemport 2
  flow 1 port eth 1 default vlan 10
  flow 2 port eth 1 vlan 11 keep → active
deploy profile rule → aim 0/1/1 → permit sn string-hex ITBS-xxxxxxxx line 1 → active
vlan 10-11
interface ethernet 1/1 → switchport mode trunk → switchport trunk allowed vlan 10-11
copy running-config startup-config
```

## 3. Ambiente corporativo (121W, ont-p2p)

Duas ONTs 121W, VLAN 20 dados + 21 voz, comunicação entre ONTs na PON.

```text
# Profiles vlan/dba/line similares ao cenário 2, com device type i40-211
# Duas rules: aim 0/1/1 e aim 0/1/2 com SNs distintos
interface gpon 0/1 → ont-p2p
vlan 20-21
interface ethernet 1/1 → switchport mode trunk → switchport trunk allowed vlan 20-21
copy running-config startup-config
```

## 4. PPPoE + WiFi + VoIP via OLT (121W router)

Toda config na OLT via `deploy profile unique`.

```text
# vlan 12 dados, vlan 13 voz no profile vlan
# line: veip vlan 12, iphost vlan 13
deploy profile wifi → aim 1 name 121W → active   # pode ficar vazio (defaults)
deploy profile unique → aim 0/1/1 name 121w-Cliente-x
  local wlan 0 ssid Cliente-x key Senha-x wifi-profile 1
  sip agent proxy-server 192.168.13.2
  sip user mode dhcp vlan 13 host 1
  sip user 1 name 606 password 606 telno 606
  local wan-config 1 dhcp nat disable service-type voip connection-type route vlan 13
  local wan-config 2 pppoe username Cliente-x password Senha-x nat enable service-type internet connection-type route vlan 12
  active
deploy profile rule → aim 0/1/1 → permit sn string-hex ITBS-xxxxxxxx line 1 → active
vlan 12-13
interface ethernet 1/1 → switchport mode trunk → switchport trunk allowed vlan 12-13
copy running-config startup-config
```

## 5. LAN-to-LAN entre ONTs

```text
deploy profile vlan → aim 1 name CLIENTE_LAN_TO_LAN → translate old-vlan 88 new-vlan 88 → active
deploy profile dba → aim 1 name 100Mbps → type 4 max 100032 → active
deploy profile line → aim 1 name 121W_LAN_TO_LAN
  device type i40-211
  tcont 1 profile dba name 100Mbps
  gemport 1 tcont 1 vlan-profile name CLIENTE_LAN_TO_LAN
  mapping mode port-vlan
  mapping 1 port eth 1 vlan 88 gemport 1
  flow 1 port eth 1 default vlan 88 → active
# Uma rule por ONT com mesmo line profile
vlan 88 → pon-switch
interface vlan-interface 88
copy running-config startup-config
```

## 6. Limite 50 Mbps simétrico

```text
deploy profile dba → aim name 50Mbps → type 4 max 50048 → active
deploy profile ds-traffic → aim name 50Mbps → ds car bandwidth 50048 → active
deploy profile line → aim name ONT_ROUTER_50Mbps
  device type i41-211
  tcont 1 profile dba name 50Mbps
  gemport 1 tcont 1 vlan-profile 1 ds-traffic-profile name 50Mbps
  mapping mode port-vlan
  mapping 1 port veip vlan 65 gemport 1
  flow 1 port veip vlan 65 keep → active
```

## Fluxo descoberta + provisionamento manual

```text
ont-find interface gpon all
show ont-find list interface gpon all
deploy profile rule
aim 0/1/1
permit sn string-hex ITBS-1790032e line 1 default line 1
active
show ont brief interface gpon all
show ont info 0/1/1
copy running-config startup-config
```

## Fluxo provisionamento automático

```text
ont-find interface gpon all
ont auto-config
ont auto-config 1 device-type i41-100 line 1
show ont brief online interface gpon all
```
