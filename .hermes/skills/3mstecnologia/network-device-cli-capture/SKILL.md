---
name: network-device-cli-capture
description: "Capture legacy network-device CLI configurations safely."
version: 1.1.0
author: Matheus Schmitt, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Networking, SSH, CLI, Capture, Security]
    related_skills: [mikrotik-routeros-ops]
---

# Legacy Network-Device CLI Capture

Use for read-only capture of sensitive running configurations from network appliances with old SSH implementations or appliance-managed interactive login prompts.

## Scope

- Read-only discovery and configuration capture.
- Preserve credentials exclusively in the approved secret manager and retrieve them only at runtime.
- Save raw configuration only in the approved local inventory workspace, mode `0600`.
- Produce a separate sanitized operational README; never reproduce raw configuration in chat, skills, Git, or public repositories.

## Procedure

1. **Route and protocol gate**
   - Confirm the management IP resolves through the intended routed peer, not a default/public path.
   - Confirm ICMP reachability where permitted.
   - Confirm the management port before attempting login.
   - If a missing specific remote prefix is confirmed by the site gateway, add only that prefix to the appropriate WireGuard peer and persist it. Check every existing peer and local route for overlap first.

2. **Secret-safe access**
   - Discover the available secret names by prefix without printing their values.
   - Read the needed values in process memory only.
   - Pin the SSH host key in a per-device `known_hosts` file.
   - Do not place passwords in shell arguments, history, audit logs, README files, or the raw-capture filename.

3. **Legacy SSH negotiation**
   - Test normal SSH first.
   - If the appliance offers only legacy cryptography, enable only the exact algorithms it advertises for that one connection, e.g. `diffie-hellman-group14-sha1` and/or `ssh-rsa`.
   - Treat appliance-native `Username`/`Password` prompts after TCP/SSH setup as a separate CLI authentication flow. Drive them interactively; do not assume the OpenSSH remote-command channel is supported.

4. **Prompt-aware capture**
   - Wait for the authenticated device prompt before sending a command.
   - For paginated output, detect the pager marker and send the documented continuation keystroke until the device prompt returns.
   - Capture only after the command fully returns to the prompt. A small capture with a pager marker is incomplete, not a backup.
   - Verify the output has a plausible complete size, line count, and no remaining pager marker before treating it as PASS.

5. **Knowledge extraction**
   - Parse the local raw file programmatically for non-sensitive facts: model/firmware, interfaces, VLAN declarations, management IPs, routes, uplinks, and service/profile types.
   - Write only those facts to the device README. Omit credential values, community strings, SNMP credentials, private keys, PSKs, and user secrets.

6. **Closeout**
   - Confirm raw capture mode `0600` and parent workspace mode `0700`.
   - Remove incomplete temporary captures rather than leaving them alongside a validated backup.
   - Report only status, safe path, byte/line count, and routing outcome.

## Evidence for any CLI execution

This skill is **read-only**. It does not apply RouterOS `add`/`set`/`remove`. When it wraps SSH (or when a mutation skill asks it to record a command boundary), each execution must preserve:

- correlation id and order (if part of a sequence);
- timestamps;
- sanitized command text;
- transport success/failure (TCP/SSH), independent of CLI errors;
- exit status (or explicit `missing`);
- stdout and stderr (or explicit `missing`).

Missing exit status, stdout, or stderr is **indeterminate**, never PASS.

Compact CLI tables that omit a field are **inconclusive**, not proof of absence. Use a deterministic follow-up query (`get`, `print where`, or a single-property projection) before declaring failure. Do not store broad `print detail` / `show running-config` in public logs.

Redact before persistence: passwords, tokens, SNMP communities, private keys, PSKs.

Mutable RouterOS workflows belong to [`mikrotik-routeros-ops`](../mikrotik-routeros-ops/SKILL.md) ([safe-ssh-mutation.md](../mikrotik-routeros-ops/references/safe-ssh-mutation.md)): one mutation per evidence boundary, then an independent state read.

## Pitfalls

- A TCP-open SSH port does not prove that non-interactive SSH remote commands work; many appliance CLIs require a pseudo-terminal and prompt-driven interaction.
- Piping password, command, and `exit` at once can cause the appliance pager or login prompt to consume later input. Wait for each expected prompt.
- Do not substitute NAT for a missing return route. Confirm the remote prefix and routed gateway first.
- Do not call a paginated `show running-config` output complete until pagination was explicitly driven to the final prompt.

## Intelbras G08 reference

For the validated G08-specific legacy SSH and paginated capture behavior, read [references/intelbras-g08-legacy-ssh.md](references/intelbras-g08-legacy-ssh.md).