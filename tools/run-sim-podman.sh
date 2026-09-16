#!/usr/bin/env bash
# Launch wasp-os simulator in the project toolchain image with X11/XWayland.
# Stock `make run-docker-image` has no X11 flags and (on Omarchy) Docker is
# sudo-only; this helper uses rootless podman.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=wasp-engine.sh
source "$ROOT/tools/wasp-engine.sh"

IMAGE="${WASP_DEV_IMAGE:-wasp-os/wasp-os-dev:0.1.0}"
NAME="${WASP_SIM_NAME:-wasp-sim}"
ENGINE="$(wasp_pick_engine)"

if ! wasp_image_exists "$ENGINE" "$IMAGE"; then
  echo "Image $IMAGE not found. Build with: ./tools/build-dev-image.sh" >&2
  exit 1
fi

RUN_ARGS=(--rm -it --name "$NAME")
wasp_fill_project_args RUN_ARGS "$ENGINE" "$ROOT"
wasp_fill_x11_args RUN_ARGS

# Stop a previous sim if still running
"$ENGINE" rm -f "$NAME" >/dev/null 2>&1 || true

exec "$ENGINE" run "${RUN_ARGS[@]}" \
  "$IMAGE" \
  bash -lc 'cd /project && make sim'
