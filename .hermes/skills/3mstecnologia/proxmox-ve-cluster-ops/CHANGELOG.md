# Changelog — proxmox-ve-cluster-ops

## [0.2.0] — 2026-09-06

- Integración con Zabbix: onboarding de un cluster PVE con el template oficial `Proxmox VE by HTTP` (1 host cluster + macros `{$PVE.*}`), token API least-privilege con ACL explícita, y hosts de nodo con `zabbix-agent2` + template Linux.
- Alertas de capacidad de storage con macro por-storage (`{$PVE.STORAGE.PUSE.MAX.WARN:"<node>/<storage>"}`).
- Trampas documentadas: `host.update` con `macros` sustituye todas las macros del host; passive check de agent2 requiere la IP de origen real del Zabbix en `Server=`; item HTTP agent type 19, item dependiente type 18 + JSONPath type 12 con `.first()`.
- Validado en un cluster PVE del cliente (8.2.7): el template HTTP descubrió 3 nodos/VMs/CTs/storage; un pool de disco al 80.4% disparó warning PR2; agent2 OK en los 3 hipervisores.

## [0.1.0] — 2026-09-06

- Publicación inicial (status DEV).
- Helper `scripts/pve.py` (Python stdlib) con autenticación API PVE 8.x por ticket (cookie `PVEAuthCookie` + `CSRFPreventionToken`), normalización de realm (`@pam`), y verbos read-only: `api-status`, `nodes`, `resources`, `guests`, `vms`, `cts`, `vm-config`, `lxc-config`, `storage`, `tasks`, `node-status`, `cluster-health` (quórum vía SSH), `ssh`.
- Credenciales resueltas solo en runtime desde entorno/Cofre (`PVE_UNIPLAC_0x_*` o `PVE_HOST/PVE_PW`); nunca logueadas.
- Validado contra cluster do cliente (PVE 8.2.7, 3 nodos, quórum Yes, 20 VMs / 2 CTs): API e SSH PASS nos 3 hosts.
- Documentación read-only, estructura SKILL.md/README/CHANGELOG, referencia de credenciales y seguridad.
- Credenciales de los 3 hosts persistidas en Cofre/Infisical (proyecto UNIPLAC, env development, `/legacy`, claves `PVE_UNIPLAC_0X_*`).