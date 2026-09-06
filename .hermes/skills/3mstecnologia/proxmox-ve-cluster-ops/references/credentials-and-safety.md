# Credenciales y seguridad — proxmox-ve-cluster-ops

Este skill NO lleva credenciales en el repositorio. Fuerza valores de entorno solo en runtime.

## Layout de credenciales en el Cofre (Infisical)

Siguiendo el patrón Madalena (proyecto por cliente, env `development`, carpeta de dispositivo). Para el cluster Proxmox de UNIPLAC:

- Proyecto: **UNIPLAC** (identificador resuelto por el gestor de secretos / Infisical)
- Entorno: `development`
- Carpeta: `/legacy`
- Claves por nodo (prefijo `PVE_UNIPLAC_0X_*`, con X = 01, 02, 03):

| Clave | Valor esperado |
|-------|----------------|
| `PVE_UNIPLAC_0X_HOST` | IP de gestão do nó (p. ex. `192.0.2.10`) |
| `PVE_UNIPLAC_0X_USERNAME` | usuario (p. ej. `root`; el helper normaliza a `root@pam` para API) |
| `PVE_UNIPLAC_0X_PASSWORD` | contraseña (`root`) |
| `PVE_UNIPLAC_0X_SSH_PORT` | puerto SSH (22) |
| `PVE_UNIPLAC_0X_API_PORT` | puerto API PVE (8006) |

Estas claves alimentan `resolve_secrets`/el entorno del helper (`--node 01` → `PVE_UNIPLAC_01_*`), coherente con el patrón usado por Madalena Network Intelligence.

## Reglas de manejo

1. **Nunca** escribir la contraseña, ticket o token en: logs, Telegram, GitHub, base de conocimiento, archivos del repo, snapshots de comandos.
2. Resolver credenciales en runtime: leer del Cofre (Identidad Infisical autorizada) o de variables de entorno; inyectarlas en el proceso sin persistirlas.
3. Para SSH usar `sshpass -p "$PASS"` con la contraseña desde variable; no en la línea de comando visible ni en argv.
4. El helper `pve.py` lee credenciales únicamente del entorno (`PVE_*`); no acepta contraseña por argumento.
5. Tras cualquier operación, revisar que no quedó credencial/ticket en caches, history de shell o archivos temporales.

## Escritura (cambios controlados) — frenos

El skill está preparado para futuras mutaciones (p. ej. `PUT /nodes/<nodo>/qemu/<vmid>/config` con `memory`/`cores`), pero **por defecto NO ejecuta escritura**:

- Requiere orden explícita del responsable (no basta contexto).
- Si el cambio es de riesgo (reboot, resize de storage, delete, cambio de red del guest), exigir confirmación adicional.
- Capturar pre-estado (config + status + storage) con `vm-config`/`node-status`/`storage` antes de mutar.
- Ejecutar UNA mutación por vez y validar con una lectura determinista tras cada una.
- Nunca mutar sin haber confirmado identidad del nodo y VMID (el nombre no es ubicación).
- Reportar siempre: qué se cambió, qué se validó, qué queda pendiente.

## Operaciones destructivas (bloqueadas por defecto)

Quedan **siempre** a la espera de autorización explícita del responsable y NUNCA automáticas:
- apagar/encender/reboot de guest o nodo;
- delete/rollback de snapshots, rearranque de cluster/reboot, factory reset;
- cambios de storage (resize, detach, mover disco), firmware upgrades;
- cambios de uplink/VLAN/routing/firewall.

## Verificación post-uso

Confirmar: `Secretos expuestos: NÃO` · `Alterações no cluster: NENGUMA` cuando la tarea fue read-only · credenciales no quedaron en ningún repositorio ni artefacto local.