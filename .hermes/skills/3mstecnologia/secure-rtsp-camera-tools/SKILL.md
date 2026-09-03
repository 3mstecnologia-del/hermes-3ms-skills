---
name: secure-rtsp-camera-tools
description: "Use when adding secure RTSP camera tools to Hermes."
version: 0.1.0
author: Matheus Schmitt, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Camera, RTSP, Docker, Plugins, Media]
    related_skills: []
---

# Secure RTSP Camera Tools

Build project-specific Hermes camera tools on top of a reusable, loopback-only RTSP snapshot helper. Keep camera credentials in a secrets manager, FFmpeg in Docker, and captured images out of the LLM context as Base64.

## When to Use

- Add snapshot or online-status functions for an RTSP camera.
- Give one project natural-language camera commands without exposing secret names.
- Reuse one generic RTSP-to-JPEG service across several project skills.
- Deliver an actual JPEG through a Hermes messaging gateway.

Do not use this workflow for continuous recording, stream relaying, detection, analytics, or periodic monitoring unless the user explicitly requests those separate capabilities.

## Architecture

```text
Natural-language request
  -> project skill
  -> project-specific native plugin tool
  -> secrets manager lookup
  -> generic loopback RTSP helper
  -> containerized FFmpeg
  -> JPEG file
  -> MEDIA: attachment delivery
```

Separate responsibilities:

- The project skill owns names, context, activation phrases, and the internal camera-to-secret mapping.
- A native user plugin provides zero-argument project tools such as `<project>_snapshot` and `<project>_camera_status`.
- The generic helper accepts an RTSP URL, captures one frame, and knows nothing about projects or secret managers.
- The messaging gateway receives only a local JPEG path, never Base64 image data.

## Prerequisites

- Docker Engine and Docker Compose Plugin.
- A functioning Hermes user-plugin installation.
- A machine identity able to read the required project/environment/path only.
- A camera URL stored as a secret; never copy it into Compose, skill prose, plugin manifests, logs, or shell arguments.
- Network reachability from the helper container to the camera.

Inventory existing port bindings, containers, host FFmpeg packages, and Hermes services before changing anything. Do not remove a pre-existing host FFmpeg package without proving no existing Hermes or system feature uses it.

## Native Hermes Interface

Use two layers instead of pretending a skill is a callable function:

1. Create a user plugin under `$HERMES_HOME/plugins/<camera-plugin>/` and register real tool schemas with `ctx.register_tool()`.
2. Create a project skill under `$HERMES_HOME/skills/<category>/<project>/SKILL.md` that maps natural language to those tools.

Tool handlers must:

- accept `args` and `**kwargs`;
- return JSON strings;
- expose no argument for a secret name when the camera is fixed by project context;
- return only sanitized error categories;
- keep access tokens and RTSP URLs in memory only.

Enable the plugin through the Hermes plugin command/configuration path, validate it with Plugin Doctor, and verify the project skill appears in a fresh Hermes session. Do not patch Hermes core tool registries or gateway media allowlists for a local integration.

## Generic RTSP Helper

Deploy a small project-local Compose stack. The HTTP API should bind only to loopback, for example `127.0.0.1:<port>`.

Required endpoints:

- `GET /health`: process health only.
- `POST /snapshot`: accepts an RTSP URL internally and returns `image/jpeg`.

FFmpeg invocation requirements:

- argv list, never `shell=True`;
- `-rtsp_transport tcp`;
- bounded socket I/O and subprocess timeouts;
- select the first video stream;
- capture exactly one frame;
- disable audio, subtitle, and data outputs;
- emit JPEG to stdout with `image2pipe`, avoiding temporary helper files;
- capture stderr without returning or logging it verbatim.

Container hardening:

- non-root UID;
- read-only root filesystem;
- `cap_drop: [ALL]`;
- `no-new-privileges`;
- bounded memory, CPU, PIDs, and log rotation;
- `restart: unless-stopped`;
- healthcheck against loopback inside the container;
- no reverse proxy or public port.

Disable request access logging because the JSON request body contains the complete RTSP URL. Return fixed errors such as `RTSP timeout`, `RTSP connection failed`, `authentication failed`, or `invalid JPEG`; never return raw FFmpeg stderr.

## Secret Retrieval

1. Load secret-manager credentials through Hermes' canonical protected environment mechanism.
2. Authenticate through the official machine-identity endpoint.
3. Keep the access token process-local and cache it in memory only until shortly before expiry when repeated calls are expected.
4. Retrieve the exact secret from the fixed project, environment, and path encoded by the project integration.
5. Pass the RTSP URL directly to the loopback helper in the HTTP body.
6. Drop all references after the request; never write the URL or token to disk.

Minimize authentication calls. A status check and a snapshot should not each create unnecessary login sessions when a still-valid in-memory access token can be reused safely.

## Snapshot Tool

The snapshot handler should:

1. Resolve the camera URL internally.
2. call the helper once;
3. validate JPEG SOI/EOI markers and dimensions;
4. write the deliverable under `$HERMES_HOME/media/<project>/` with directory mode `0700` and file mode `0600`;
5. return JSON containing success, camera label, absolute image path, resolution, byte size, and elapsed time;
6. include a `MEDIA:/absolute/path.jpg` field for explicit delivery.

Never claim success from HTTP 200 alone; a valid JPEG is the acceptance criterion.

## Status Tool

Status means a real one-frame probe, not helper health:

- `ONLINE`: a frame was retrieved and validated within the timeout.
- `OFFLINE`: no valid frame was obtained.

Discard the status frame instead of writing it. Return only a sanitized reason. Opening a TCP socket or receiving an RTSP response is insufficient to label the camera online.

## Media Delivery

Hermes messaging adapters recognize `MEDIA:/absolute/path.ext` in the assistant's final response and deliver supported files natively. Arbitrary plugin tools are not guaranteed to be auto-appended by the gateway's built-in producer allowlist.

Therefore the project skill must instruct the model to copy the exact `MEDIA:` tag returned by the successful snapshot tool into the final response. Do not embed JPEG bytes or Base64 in tool output or prompt context. Verify actual platform delivery with a real frame; a unit test of the path field alone is not Telegram delivery proof.

## Testing

Use RED-GREEN-REFACTOR for both helper and plugin client.

Unit tests must cover:

- RTSP/RTSPS URL validation;
- TCP transport and one-frame FFmpeg argv;
- subprocess timeout;
- no shell invocation;
- credential-free errors;
- JPEG marker/dimension validation;
- secure output path and metadata-only result;
- status discarding the frame;
- plugin registration through Plugin Doctor.

End-to-end verification must report independently:

- secret-manager authentication;
- secret read;
- helper health;
- RTSP frame retrieval;
- JPEG validation;
- resolution, size, and capture duration;
- tool registration and skill discovery;
- actual `MEDIA:` image arrival in the target messaging platform.

A helper healthcheck passing does not satisfy camera status, and a local JPEG existing does not satisfy Telegram delivery.

## Safe Debugging

When capture fails, preserve the no-leak boundary:

1. Reproduce with one snapshot request.
2. Check secret authentication and read as booleans/status codes only.
3. Parse the RTSP URL only in memory and test DNS/TCP reachability without printing host, path, username, or password.
4. Classify FFmpeg stderr in memory into fixed safe reasons; do not print raw stderr.
5. Distinguish helper health, network reachability, RTSP negotiation, camera authentication, and JPEG encoding.
6. Stop if credentials are revoked or camera routing requires user/network changes; do not alter the secret manager or firewall implicitly.

## Pitfalls

- A skill file alone does not create callable tools; use a native plugin for functions.
- Do not expose a generic `camera_snapshot(secret_name)` interface when project context can remove the parameter.
- Do not log HTTP request bodies, raw exceptions, subprocess argv, or FFmpeg stderr.
- Do not put the RTSP URL into container environment variables or Docker command arguments; those persist in inspection surfaces.
- Do not introduce a second reverse proxy for a loopback helper.
- Do not report attachment delivery as PASS until the messaging platform receives the real image.
- Do not broaden machine-identity permissions to solve a path, environment, or routing mistake.

## Verification

The integration is complete only when native project tools are registered, the skill is discoverable, a real frame passes JPEG validation, the helper remains loopback-only, no sensitive value appears in logs, and the real JPEG is delivered through the requested messaging platform.
