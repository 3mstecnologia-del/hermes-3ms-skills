# Intelbras OLT G08 — legacy SSH capture notes

Validated against an Intelbras G08 in a routed management subnet.

## Transport gate

- The Hermes WireGuard peer must include the exact OLT management subnet when the site gateway confirms it owns the route.
- Validate VPS route selection and ICMP before SSH.
- The G08 management protocol was SSH/TCP 22.

## SSH behavior

The appliance advertised legacy algorithms:

- KEX: `diffie-hellman-group14-sha1`
- Host key: `ssh-rsa`

Use these only in the per-device access wrapper, with a pinned local known-hosts file. The normal SSH remote-command channel closed immediately; a pseudo-terminal session was required.

The SSH username selects the appliance login identity, then the appliance presents its own password prompt. Send the runtime password only after detecting that prompt, and wait for `G8>` before issuing CLI commands.

## Running-config capture

`show running-config` paginates with a marker beginning `press ENTER to next line`. A collector must send Enter for every marker and continue until the final `G8>` prompt. A capture that ends at a pager marker is incomplete and should be deleted.

## Safe persistence

Store raw output under the client/device inventory `backups/` folder with a timestamped filename and mode `0600`. Generate a README from parsed non-sensitive facts only. Do not place raw config, credentials, SNMP communities, or device secrets in a skill or public repository.
