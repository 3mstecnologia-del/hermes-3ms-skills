# Changelog — proxmox-ve-cluster-ops

## [0.1.0] — 2026-09-06

- Publicación inicial (status DEV).
- Helper `scripts/pve.py` (Python stdlib) con autenticación API PVE 8.x por ticket (cookie `PVEAuthCookie` + `CSRFPreventionToken`), normalización de realm (`@pam`), y verbos read-only: `api-status`, `nodes`, `resources`, `guests`, `vms`, `cts`, `vm-config`, `lxc-config`, `storage`, `tasks`, `node-status`, `cluster-health` (quórum vía SSH), `ssh`.
- Credenciales resueltas solo en runtime desde entorno/Cofre (`PVE_UNIPLAC_0x_*` o `PVE_HOST/PVE_PW`); nunca logueadas.
- Validado contra cluster do cliente (PVE 8.2.7, 3 nodos, quórum Yes, 20 VMs / 2 CTs): API e SSH PASS nos 3 hosts.
- Documentación read-only, estructura SKILL.md/README/CHANGELOG, referencia de credenciales y seguridad.
- Credenciales de los 3 hosts persistidas en Cofre/Infisical (proyecto UNIPLAC, env development, `/legacy`, claves `PVE_UNIPLAC_0X_*`).