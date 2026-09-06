# Proxmox VE Cluster Operations — skill Madalena

Skill operacional para clusters **Proxmox VE** (PVE 8.x) de 3MS Tecnología. Preferencia por la **API oficial** (`/api2/json`, puerto 8006) y **SSH** (puerto 22) como herramienta complementaria para diagnóstico que requiera terminal.

- **Read-only por defecto.** No ejecuta cambios en VMs, containers, hardware, memoria, CPU, storage ni configuración de cluster sin autorización explícita y paso a paso.
- Diseñada para futuros cambios controlados (p. ej. redimensionar memoria de una VM) **sin ejecutarlos** en esta fase.

## Cómo funciona

- Helper `scripts/pve.py` (Python stdlib) que: autentica contra la API PVE 8.x por ticket (cookie `PVEAuthCookie` + `CSRFPreventionToken`), y expone verbos read-only (`api-status`, `nodes`, `resources`, `guests`, `vms`, `cts`, `vm-config`, `lxc-config`, `storage`, `tasks`, `node-status`, `cluster-health`), más un verbo `ssh` para terminal.
- Las credenciales se resuelven **solo en runtime** (entorno/Cofre) y nunca se persisten ni se loguean.

## Requisitos

- Python 3.9+ (stdlib). Para `ssh`/`cluster-health`: `sshpass` y `ssh`.
- Hosts alcanzables en `8006` y `22`.
- Credenciales en runtime: por node-prefix `PVE_UNIPLAC_01_*` (ver `references/credentials-and-safety.md`) o directas `PVE_HOST`/`PVE_PW`/`PVE_USER`.

## Ejemplos de uso

```bash
python3 scripts/pve.py --node 01 api-status     # autenticación + versión
python3 scripts/pve.py --node 01 cluster-health # quórum corosync (SSH)
python3 scripts/pve.py --node 01 resources      # VMs/CTs/storage por nodo
python3 scripts/pve.py --node 01 vm-config pve03 110 --keys name,memory,cores,scsi0
python3 scripts/pve.py --node 01 ssh 'hostname'
```

## Estatísticas de validação (cluster do cliente)

- Versión PVE: 8.2.7 en los 3 nodos.
- Nodos: 3 (pve01/02/03), todos online.
- Quórum: **Yes** (esperado 3, quorum 2, votos 3).
- VMs: 20 (18 running / 2 stopped). Containers: 2 (1 running / 1 stopped).
- Storage: 7 pools (disco_ssd, windows_nfs, pbs-hp2, local, local-lvm, disco_hdd, pbs-3ms).

## Limitaciones y cuidado con operaciones destructivas

Ver `SKILL.md` (Pitfalls) y `references/credentials-and-safety.md`. Resumen: no mutar sin orden; capturar pre-estado; una mutación por vez; validar con lectura; mantener credenciales fuera de cualquier repositorio/log/chat.