---
name: proxmox-ve-cluster-ops
description: "Operate a Proxmox VE cluster via API+SSH (read-only by default). Use when working with Proxmox PVE: cluster status, quorum, nodes, VMs, LXC containers, storage, tasks, resource audit, or preparing controlled VM/CT changes."
version: 0.1.0
metadata:
  hermes:
    tags: [proxmox, pve, virtualization, cluster, api, ssh, read-only, hypervisor]
    status: DEV
    related_skills: [infisical-machine-identity]
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