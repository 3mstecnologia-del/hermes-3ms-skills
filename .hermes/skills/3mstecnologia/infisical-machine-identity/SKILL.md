---
name: infisical-machine-identity
description: Use when configuring Infisical machine access safely.
version: 0.1.0
author: 3MS Tecnologia, Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Infisical, Secrets, Machine Identity, Universal Auth, Security]
    related_skills: []
---

# Infisical machine identity

## When to use
Use for server or workload tasks that must configure, validate, or troubleshoot Infisical access with Machine Identities, especially Universal Auth on VPSes or Docker hosts.

## Workflow
1. **Confirm the Infisical endpoint first.**
   - Prefer an explicit URL from the user.
   - If the URL is not given, look only in directly relevant local config/examples for `INFISICAL_SITE_URL`/`INFISICAL_URL`; do not widen the search beyond the host's app config.
   - Validate connectivity with a minimal HTTPS request before using credentials.

2. **Check for an existing client path with the smallest possible surface area.**
   - Check for `infisical` CLI and Docker.
   - Prefer the already-installed CLI when present.
   - If no CLI is present and Docker exists, prefer the official `infisical/cli` image over installing host packages; this matches Docker-first and avoids unnecessary host changes.

3. **Explain each step before running it when the user wants live oversight.**
   - Use the format `PASSO X — <action>`.
   - In 1–2 sentences state the goal and the exact command/configuration you are about to use.
   - After execution, show only the minimum validating output.

4. **Authenticate with Universal Auth without echoing secrets.**
   - Use `POST /api/v1/auth/universal-auth/login` or `infisical login --method universal-auth`.
   - Pass the client ID and client secret via environment variables or process-local variables; never print them back.
   - Treat success as: token issued plus non-sensitive metadata such as token type or TTL.

5. **Validate access by reading metadata before reading secrets.**
   - Query accessible projects/workspaces first.
   - Then enumerate accessible environments from the project metadata when available.
   - If projects/workspaces are empty after successful login, stop and report that the identity authenticates but is not attached to any accessible project. Do not guess project IDs and do not brute-force environments.

6. **Perform read-only secret validation without exposing values.**
   - List secret keys/names only.
   - Start with the environment metadata and a root-path read, then repeat with `recursive=true` when the root looks empty; many teams keep secrets under subfolders, so a non-recursive `/` read can falsely look like no access.
   - Do not call commands or API options that print raw values when a masked or metadata-only path exists.
   - Report names, paths, project names, and environment slugs only.

7. **Persist only what is required for post-reboot authentication.**
   - If persistence is required, store only the endpoint and Machine Identity credentials in a root-only local file outside any repo, for example under `/etc/<app-or-tool>/` with `0700` directory and `0600` file permissions.
   - Provide a small root-only wrapper or deterministic invocation path that can re-authenticate on demand after reboot.
   - Make the wrapper expose read-only operations that are safe to demonstrate later, such as login status, project listing, environment listing, and secret-key listing without values.
   - Prefer on-demand re-authentication from stored Universal Auth credentials over persisting a long-lived access token, because access tokens expire and the client credentials are the intended bootstrap material.
   - Do not install a daemon or extra service unless it is actually needed for the requested steady-state behavior.

8. **Verify local handling of credentials after any state change.**
   - Check that no client ID, client secret, or fetched secret values landed in Git repos, documentation, or other versionable paths.
   - Include agent-side command caches and temporary terminal artifacts in this check; command snapshots can retain inline credentials even when the final configuration is clean.
   - On Hermes hosts, inspect transient terminal snapshot/cache locations before declaring success; see `references/hermes-local-persistence.md`.
   - If a local cache artifact captured credentials, remove that artifact and re-check before declaring success.

## Reporting

For a concrete Linux host pattern using a root-only env file, a root-only wrapper, and post-run cleanup checks on Hermes-managed shells, see `references/hermes-local-persistence.md`.

- Use objective PASS/FAIL lines for connectivity, Machine Identity, Universal Auth, authentication, persistence after reboot, accessible projects, accessible environments, and read-only secret access.
- Explicitly state `Valores de secrets exibidos: NÃO` / `Secrets expostos: NÃO` when that was preserved.
- Explicitly state `Alterações no cofre: NENHUMA` when the task was read-only.
- If blocked by permissions, name the missing permission or missing project attachment exactly and stop there.

## Pitfalls
- Stop after successful login if project listing is empty; Universal Auth success proves the identity exists, but not that it has any project-level secret access.
- Repeat secret listing with recursive folder traversal before concluding an environment is empty, because Infisical projects often store secrets below `/` and a shallow read returns zero keys.
- Prefer official CLI help or API docs before guessing Machine Identity flags; Infisical machine-auth flows differ from user login flows.
- Check agent-side shell caches and transcript snapshots after any command that carried inline credentials, because the terminal layer itself can retain secrets outside the final destination path.
- Keep credentials out of repo-tracked or document paths because server secret-bootstrap tasks often leave behind local helper files that are easy to commit later.
- Do not persist access tokens as the only recovery path because they can expire independently of the VPS lifecycle; persist the approved bootstrap credentials with restricted permissions instead.
