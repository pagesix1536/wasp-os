#!/usr/bin/env bash
# Build wasp-os/wasp-os-dev (Ubuntu 24.04 toolchain) with rootless podman.
# Replaces `make build-docker-image` on hosts where Docker is sudo-only
# (Omarchy) or where `docker` is not the engine we run the sim/build in.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=wasp-engine.sh
source "$ROOT/tools/wasp-engine.sh"

ENGINE="$(wasp_pick_engine)"
# shellcheck disable=SC1091
source "$ROOT/tools/docker/.env"
VER="${DOCKER_IMG_VER:-0.1.0}"
IMAGE_VER="wasp-os/wasp-os-dev:${VER}"
IMAGE_LATEST="wasp-os/wasp-os-dev:latest"

echo "=== $ENGINE build $IMAGE_VER ==="
"$ENGINE" build \
  --tag "$IMAGE_VER" \
  --tag "$IMAGE_LATEST" \
  --build-arg "DOCKER_IMG_VER=${VER}" \
  --file "$ROOT/tools/docker/Dockerfile" \
  "$ROOT"

echo "OK: $IMAGE_VER"
"$ENGINE" image inspect "$IMAGE_VER" --format '{{.Id}} {{.Created}}' 2>/dev/null \
  || "$ENGINE" image inspect "$IMAGE_VER" | head -5
