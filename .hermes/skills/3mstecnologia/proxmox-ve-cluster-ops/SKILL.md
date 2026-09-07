---
name: proxmox-ve-cluster-ops
description: "Operate a Proxmox VE cluster via API+SSH (read-only by default) and integrate with Zabbix. Use for cluster status, quorum, nodes, VMs, LXC containers, storage, tasks, resource audit, capacity alerts, or Zabbix onboarding of a PVE cluster."
version: 0.2.0
metadata:
  hermes:
    tags: [proxmox, pve, virtualization, cluster, api, ssh, read-only, hypervisor, zabbix, monitoring]
    status: DEV
    related_skills: [infisical-machine-identity, zabbix-snmp-monitoring]
---

# Proxmox VE Cluster Operations

Atua como engenheiro senior de virtualização sobre clusters **Proxmox VE** (PVE 8.x). Responde em português brasileiro. **Read-only por defecto**: este skill inspecciona y diagnostica; NUNCA muta VMs, containers, hardware, memoria, CPU, storage ni configuración de cluster sin autorización explícita y paso a paso.

La salida real del API del cluster prevalece sobre cualquier ejemplo de esta skill. No inventes endpoints ni campos; valida contra `/api2/json` o el equipamiento real.

## Flujo obligatorio

```
IDENTIFICAR → LEER (API) → DIAGNOSTICAR → PLANIFICAR → (AUTORIZACIÓN) → CAMBIO MÍNIMO → VALIDAR → PERSISTIR → REPORTAR
```

Read-only precede cualquier escritura. Una mutación por vez. Validar con una lectura determinista después de cada mutación.

## Cuándo usarla

- Validar acceso API / SSH a los hosts del cluster.
- Consultar estado del cluster, quórum, nodos, VMs, containers, storage, tasks, estado de guests.
- Identificar en qué nodo vive cada VM/CT y su configuración (CPU/RAM/discos).
- Auditar recursos o preparar cambios controlados (p. ej. redimensionar memoria de una VM) **sin ejecutarlos**.
- Diagnóstico que requiera terminal (quórum corosync, red, etc.) vía SSH.

No usar para: operar otras plataformas, o para mutar el cluster sin autorización explícita del responsable.

## Prerrequisitos

- Hosts del cluster alcanzables por `8006` (API PVE) y `22` (SSH). Ver credenciales abajo.
- `python3` (stdlib). Para verbo `ssh` y `cluster-health`: `sshpass` + `ssh` en el host.
- Credenciales resueltas SOLO en runtime desde el Cofre/Infisical (o vars de entorno); nunca escritas en archivos del repo ni en logs/Telegram/Git.

## Autenticación (API)

PVE 8.x expone la API REST en `https://<host>:8006/api2/json`. Login por contraseña (`POST /access/ticket` con `username`/`password`) devuelve el **ticket en el JSON**; ese ticket ES el valor de la cookie `PVEAuthCookie`. En PVE 8.x NO llega via `Set-Cookie`; por eso el helper la extrae del body. Para endpoints GET basta cookie; para escritura se requiere además cabecera `CSRFPreventionToken`. El helper `scripts/pve.py` maneja ticket + cookie + CSRF.

Realm: el usuario API nunca lleva realm vacío; si la credencial es `root`, se normaliza a `root@pam` (`@pam` por defecto). Qirola exacta de autenticación en `references/credentials-and-safety.md`.

## Cómo ejecutar

```bash
# Rellenar entorno desde Cofre (runtime) p. ej. PVE_UNIPLAC_01_* ; o vars directas:
export PVE_HOST=192.0.2.10 PVE_PW=... PVE_USER=root@pam

python3 scripts/pve.py --node 01 api-status
python3 scripts/pve.py --node 01 nodes
python3 scripts/pve.py --node 01 resources          # todo el cluster (VM/CT/storage por nodo)
python3 scripts/pve.py --node 01 cluster-health     # quórum corosync vía SSH
python3 scripts/pve.py --node 01 vms [nodo] | cts [nodo] | guests [nodo]
python3 scripts/pve.py --node 01 vm-config <nodo> <vmid> [--keys cores,memory,sockets,scsi0]
python3 scripts/pve.py --node 01 lxc-config <nodo> <vmid>
python3 scripts/pve.py --node 01 storage | tasks <nodo> [--limit N] | node-status <nodo>
python3 scripts/pve.py --node 01 ssh '<comando>'   # terminal complementario
```

Usar el helper vía la herramienta `terminal` de Hermes. Si se resuelven credenciales desde Cofre, hacerlo en una sola inyección de entorno sin imprimir valores.

## Quiké referencia (verbos read-only)

| Verbo | Fuente | Qué devuelve |
|-------|--------|--------------|
| `api-status` | API | versión/release; prueba autenticación |
| `nodes` | API | nodos del cluster, status, uptime, cpu/mem/disk |
| `resources` | API | cluster completo: VMs, containers, storage, sdn por nodo |
| `cluster-health` | SSH | `pvecm status` → name, quorate, expected/votes, quorum |
| `vms` / `cts` / `guests` | API | VMs (qemu) / containers (lxc) / ambos por nodo |
| `vm-config` / `lxc-config` | API | configuración (cores, sockets, memory, scsi*, net0, boot…) |
| `storage` | API | pools de storage, tipo, contenido, shared |
| `tasks` | API | tareas recientes del nodo (upid, type, status) |
| `node-status` | API | estado resumido del nodo |
| `ssh '<cmd>'` | SSH | comando privilegiado de diagnóstico |

## Procedimiento de validación (checklist de una audit)

1. `api-status` en cada host → PASS/FAIL por host.
2. `ssh 'hostname'` en cada host → mapea IP→nombre de nodo, comprueba SSH.
3. `nodes` y `resources` → membresía y salud.
4. `cluster-health` (SSH) → quórum corosync.
5. `guests <node>` / `vms` por nodo → inventario y ubicación de cada VM/CT.
6. `vm-config` de una VM objetivo → RAM/vCPU/discos.
7. `storage` y `tasks` → pools y actividad.
8. Reportar con líneas PASS/FAIL objetivas y fuente (API vs SSH).

Criterio de completitud: cada ítem del pedido tiene un comando y su salida verificada; nada se asume sin lectura.

## Integración con Zabbix (onboarding de un cluster PVE)

El template oficial **`Proxmox VE by HTTP`** (HTTP agent, type 19) descubre el clúster completo desde UN host: quórum, nodos, VMs, CTs, storage — con la API `8006` y un **token API least-privilege**. NO dupliques coleta creando N hosts con el template HTTP (cada uno redescubriría todo). Patrón validado en un cluster PVE 8.2.7 del cliente:

1. **Token mínimo en PVE**: usuario propio (p. ej. `pve-monitor@pve`) con role custom de auditoría (`Datastore.Audit, Sys.Audit, VM.Audit`) y token con ACL explícita en `/` porque con `privsep=1` el token NO hereda la ACL del usuario:
   ```bash
   pveum user add pve-monitor@pve --comment "Zabbix 7.0 Proxmox VE by HTTP (read-only)"
   pveum role add PveMonitorAudit --privs Datastore.Audit,Sys.Audit,VM.Audit
   pveum acl modify / --token "pve-monitor@pve!zabbix-http" --role PveMonitorAudit
   pveum user token add pve-monitor@pve zabbix-http --privsep 1   # capturar secret (se muestra UNA vez)
   ```
2. **Cofre**: persistir `PVE_0X_ZABBIX_TOKEN_ID` y `..._SECRET`.
3. **1 host cluster** en Zabbix (grupos `Hypervisors`, grupo del cliente) con template `Proxmox VE by HTTP` y macros: `{$PVE.URL.HOST}`, `{$PVE.URL.PORT}`, `{$PVE.TOKEN.ID}`, `{$PVE.TOKEN.SECRET}`.
4. **Capacidad de storage**: el template emite triggers `Storage [<node>/<storage>] high filesystem space usage` con macro `{$PVE.STORAGE.PUSE.MAX.WARN:"<node>/<storage>"}` (con contexto). Para alertar antes del default (90%) define la macro **con contexto por storage** en el host cluster, p. ej. `{$PVE.STORAGE.PUSE.MAX.WARN:"pve01/disco_ssd"}=80`. Verificar soporte de RBD compartido: el item `proxmox.node.disk` del LLD storage puede quedar unsupported en pools RBD (valor del endpoint `/nodes/<node>/storage/<pool>/status` → `used`/`total`). Si el trigger no dispara, usar una macro de host o item HTTP dedicado sobre ese endpoint.
5. **Hosts de nodo separados** (opcional, para SO del hipervisor): `zabbix-agent2` ya instalado + template `Linux by Zabbix agent` + `ICMP Ping`. En PVE la config agent2 suele venir con `Server=`/`ServerActive=` apuntando a un server; verifica con el LOG qué IP de origen usa el Zabbix real para el passive check y ajusta `Server=` a esa(s) origen(es) (no solo al IP del server en otra subred/NAT — el passive check falla "empty response" si la origem de red no está en `Server=`).
6. **Validación real** (no confiar en `host.create`): leer availability (`available=2` erro), `agent.ping`/`system.uptime` con `lastclock` reciente, y triggers FIRE de storage; re-leer macros para confirmar que sobrevivieron.

### Trampas de integración
- **host.update con `macros` sustituye TODAS las macros del host**: enviar solo un subconjunto borra las demás. Re-relanzar SIEMPRE el conjunto completo (todas las `{$PVE.*}` + las custom por storage).
- Cuenta de macros: al sobrescribir threshold de storage, incluye las 4 macros PVE de auth/URL junto con las de threshold en el MISMO update, o pierdes la coleta HTTP del template (itens pasan unsupported / "URL rejected").
- Item HTTP agent manual: type correcto es **19** (no 18=simple check). Para ITEM DEPENDIENTE el tipo es 18 con `master_itemid` + `delay:"0"` y preprocess JSONPath `type` **12** con `.first()` (no 11). El tipo 11 (JSONPath) en item.create exige `master_itemid`; un item no-dependiente con JSONPath falla.
- El host name sanitizado en Zabbix no admite `+` ni caracteres no-ASCII (usar `Proxmox-<CLUSTER>`).

## Escritura (preparada, NO ejecutada por defecto)

El skill nace preparado para cambios controlados (p. ej. `PUT /nodes/<nodo>/qemu/<vmid>/config` con `memory`/`cores` vía API, o edición por SSH). Reglas antes de cualquier mutación:

- Requiere autorización explícita del responsable y, si hay riesgo, una confirmación extra.
- Capturar pre-estado (config + status) antes de mutar.
- Una mutación por vez; validar con una lectura determinista tras cada una.
- No tocar VM/CT/hardware/storage/config sin orden expresa.

Detalle de operaciones destructivas y sus frenos: `references/credentials-and-safety.md`.

## Pitfalls

- **Ticket de PVE 8.x**: llega en el JSON del login, no como `Set-Cookie`. Si copias fragmentos de clientes viejos que esperan `PVEAuthCookie` por header, no funcionará.
- No loguear la credencial raíz ni el ticket; inyectar siempre desde entorno/Cofre.
- No inferir ubicación de una VM por su nombre; la ubicación real la da `resources`/`guests`.
- El agente QEMU de un guest puede estar apagado; entonces no consultes IP por agente, usa inventario/ARP/red (read-only).
- Ownership/red: la red de un guest puede ser L2 de un bridge sin IP en el host (p. ej. `vmbr1`); el host no puede ARP por IPs de esa red. No concluir ausencia por eso.
- `verify_ssl=False` es necesario porque PVE usa certificado auto-firmado; limitar siempre a red confiable y credenciales least-privilege.
- La salida real del API prevalece; no inventar campos si `resources`/`config` no los exponen.

## Verificación

La skill está validada si: `api-status` y `ssh 'hostname'` pasan en los 3 hosts; `nodes` muestra todos online; `cluster-health` reporta `Quorate: Yes` con el quórum esperado; `resources` lista VMs/CTs con su nodo; `vm-config` devuelve RAM/vCPU/discos de una VM objetivo; y nada fue mutado (re-lectura de estado igual a pre-estado).