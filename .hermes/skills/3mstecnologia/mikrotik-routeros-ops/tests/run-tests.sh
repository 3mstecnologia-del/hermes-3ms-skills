#!/bin/sh
# Run contract tests inside Docker. Host needs only Docker — no Python/pip.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
docker run --rm \
  -v "$HERE:/tests:ro" \
  -w /tests \
  python:3.12-slim \
  python -m unittest discover -s /tests -v
