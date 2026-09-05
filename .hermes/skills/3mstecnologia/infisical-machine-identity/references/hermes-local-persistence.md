# Hermes local persistence pattern for Infisical machine identities

Use this pattern on Linux servers when the machine must keep Infisical access across reboots without leaving secrets in repo paths.

## Recommended local layout

- Directory: `/etc/infisical/`
- Credential file: `/etc/infisical/<machine-name>.env`
- Wrapper: `/usr/local/bin/<machine-name>-infisical`

Permissions:

- `/etc/infisical/` → `0700`, owner `root:root`
- env file → `0600`, owner `root:root`
- wrapper → `0700`, owner `root:root`

Store only:

- Infisical base URL
- Machine Identity client ID
- Machine Identity client secret

Do not store:

- exported plaintext secret values
- Git-tracked helper files
- long-lived access tokens as the only recovery path

## Wrapper behavior

The wrapper should:

1. load the root-only env file;
2. authenticate on demand with Universal Auth;
3. expose only safe read-only helper operations such as:
   - login status
   - project listing
   - environment listing
   - secret-key listing without values

On Docker-first hosts, prefer the official `infisical/cli` container as the execution path instead of installing extra host packages.

## Validation sequence

1. Run the wrapper from a fresh shell/process.
2. Confirm authentication succeeds without relying on exported variables from the current session.
3. List accessible projects.
4. List accessible environments.
5. List secret keys only, never secret values.

## Cleanup check on Hermes hosts

If credentials were passed inline to shell commands during setup, inspect Hermes terminal snapshot/cache artifacts before finishing.

Why: Hermes-managed shell wrappers can persist the exact executed command line in transient snapshot files even when the final destination paths are correct and the final report is redacted.

At minimum, verify that no credential-bearing artifact remains in Hermes-managed terminal cache locations before declaring the host clean.
