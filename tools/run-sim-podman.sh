#!/usr/bin/env bash
# Launch wasp-os simulator in the project Podman image with X11 on Fedora.
# Stock `make run-docker-image` uses --userns=host and no X11/SELinux flags;
# that fails to write the bind mount and cannot open SDL windows here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

IMAGE="${WASP_DEV_IMAGE:-wasp-os/wasp-os-dev:0.1.0}"
NAME="${WASP_SIM_NAME:-wasp-sim}"

if ! podman image exists "$IMAGE"; then
  echo "Image $IMAGE not found. Build with: make build-docker-image" >&2
  exit 1
fi

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set; cannot open SDL window." >&2
  exit 1
fi

# Allow local X clients (XWayland)
if command -v xhost >/dev/null 2>&1; then
  xhost +local: >/dev/null 2>&1 || true
fi

XAUTH="${XAUTHORITY:-}"
AUTH_ARGS=()
if [[ -n "$XAUTH" && -r "$XAUTH" ]]; then
  AUTH_ARGS+=(--volume="${XAUTH}:${XAUTH}:ro" --env=XAUTHORITY="${XAUTH}")
fi

# Stop a previous sim if still running
podman rm -f "$NAME" >/dev/null 2>&1 || true

exec podman run --rm -it \
  --name "$NAME" \
  --security-opt label=disable \
  --volume="${ROOT}:/project/:z" \
  --volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
  "${AUTH_ARGS[@]}" \
  --env=DISPLAY="${DISPLAY}" \
  --env=SDL_VIDEODRIVER=x11 \
  --userns=keep-id \
  --user="$(id -u):$(id -g)" \
  --net=host \
  --entrypoint="" \
  "$IMAGE" \
  bash -lc 'cd /project && make sim'
