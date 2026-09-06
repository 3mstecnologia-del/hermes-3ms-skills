# API y validación — proxmox-ve-cluster-ops

## Endpoints API PVE usados (base `https://<host>:8006/api2/json`)

| Acción | Método/Ruta | Notas |
|--------|-------------|-------|
| Login | `POST /access/ticket` | body `username`/`password`; devuelve `ticket` (JSON) y `CSRFPreventionToken`. El ticket ES el `PVEAuthCookie`. |
| Versión | `GET /version` | versión/release/repoid |
| Nodos | `GET /nodes` | pertenencia, status, CPU/mem/disk |
| Estado nodo | `GET /nodes/<node>/status` | cpu, mem, maxmem, disk… |
| Tasks | `GET /nodes/<node>/tasks` | upid, type, status |
| VMs | `GET /nodes/<node>/qemu` | lista qemu |
| Contenedores | `GET /nodes/<node>/lxc` | lista lxc |
| Config VM | `GET /nodes/<node>/qemu/<vmid>/config` | cores, sockets, memory, scsi*, net0, boot… |
| Config CT | `GET /nodes/<node>/lxc/<vmid>/config` | idem contenedores |
| Storage | `GET /storage` | pools de storage (tipo, content, shared) |
| Recursos cluster | `GET /cluster/resources` | VM/CT/storage/sdn de todo el cluster con su nodo |
| (escritura) | `PUT/POST /nodes/<node>/qemu/<vmid>/config` etc. | requiere CSRF + cookie; NO ejecutar sin autorización |

## Notas de autenticación PVE 8.x

- El login devuelve el ticket en el **cuerpo JSON**, no por `Set-Cookie`. Envía `Cookie: PVEAuthCookie=<ticket>` en las siguientes llamadas.
- GETs readonly solo necesitan la cookie; escrituras requieren además `CSRFPreventionToken`.
- El usuario API necesita realm: `root` → `root@pam` (el helper lo normaliza).
- Certificado auto-firmado → `verify_ssl=False`, solo sobre red confiable.

## Scripts de validación reproducible

Batería mínima (read-only) para certificar una skill nueva contra un cluster:

```bash
python3 scripts/pve.py --node 01 api-status      # PASS/FAIL auth+versión
python3 scripts/pve.py --node 01 ssh 'hostname'  # PASS/FAIL SSH; mapea IP→node
python3 scripts/pve.py --node 01 nodes           # todos online
python3 scripts/pve.py --node 01 cluster-health  # Quorate Yes + quórum
python3 scripts/pve.py --node 01 resources       # inventario VMs/CTs por nodo
python3 scripts/pve.py --node 01 vm-config <nodo> <vmid> --keys name,memory,cores,scsi0
python3 scripts/pve.py --node 01 storage
```

Reportar cada ítem con su fuente (API vs SSH) y estado objetivo (PASS/FAIL), y confirmar que ninguna re-lectura difiere del pre-estado (nada mutado).