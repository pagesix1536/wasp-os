#!/usr/bin/env bash
# Build PineTime micropython.zip in the project Podman image, and/or OTA it
# to a watch already running the wasp bootloader (PineDFU mode).
#
# Usage:
#   ./tools/build-flash-pinetime.sh build    # only build
#   ./tools/build-flash-pinetime.sh flash    # only OTA existing zip
#   ./tools/build-flash-pinetime.sh all      # build then flash (default)
#   ./tools/build-flash-pinetime.sh shell    # interactive build container
#
# Prerequisites:
#   - podman + image wasp-os/wasp-os-dev:0.1.0  (make build-docker-image)
#   - submodules initialized once:  make submodules  (or first 'build' does it)
#   - SoftDevice s132 (see ensure_softdevice below; Nordic URL often 403)
#   - for flash: watch in OTA/PineDFU (hold side button ~5s), phone BT off
#   - for flash: .venv-dfu with bleak + tools/bleak_legacy_dfu.py
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

IMAGE="${WASP_DEV_IMAGE:-wasp-os/wasp-os-dev:0.1.0}"
ZIP="${WASP_MPY_ZIP:-$ROOT/build-pinetime/micropython.zip}"
BOARD="${BOARD:-pinetime}"
CMD="${1:-all}"

podman_build() {
  if ! command -v podman >/dev/null 2>&1; then
    echo "podman not found" >&2
    exit 1
  fi
  if ! podman image exists "$IMAGE"; then
    echo "Image $IMAGE not found. Run: make build-docker-image" >&2
    exit 1
  fi

  # shellcheck disable=SC2086
  podman run --rm \
    --name wasp-build \
    --volume="${ROOT}:/project/:z" \
    --userns=keep-id \
    --user="$(id -u):$(id -g)" \
    --net=host \
    --entrypoint="" \
    "$IMAGE" \
    bash -lc "cd /project && $*"
}

ensure_softdevice() {
  local dst="micropython/ports/nrf/drivers/bluetooth/s132_nrf52_6.1.1"
  local hex="$dst/s132_nrf52_6.1.1_softdevice.hex"
  local src="bootloader/lib/softdevice/s132_nrf52_6.1.1"

  if [[ -f "$hex" ]]; then
    return 0
  fi

  echo "SoftDevice hex missing (Nordic download often fails with HTTP 403)."
  if [[ ! -d bootloader/lib/softdevice ]]; then
    echo "Initializing submodules (includes bootloader SoftDevice)..."
    podman_build "make submodules"
  fi

  if [[ -f "$src/s132_nrf52_6.1.1_softdevice.hex" ]]; then
    echo "Copying SoftDevice from bootloader submodule → $dst"
    mkdir -p "$dst"
    cp -a "$src"/. "$dst"/
  else
    echo "Cannot find SoftDevice. Try: make submodules && ensure bootloader has s132." >&2
    exit 1
  fi
}

do_build() {
  echo "=== Ensuring SoftDevice ==="
  ensure_softdevice

  if [[ ! -d micropython/ports/nrf ]]; then
    echo "=== make submodules ==="
    podman_build "make submodules"
    ensure_softdevice
  fi

  echo "=== make BOARD=${BOARD} micropython (uses wasp.toml) ==="
  podman_build "make -j\$(nproc) BOARD=${BOARD} micropython"

  if [[ ! -f "$ZIP" ]]; then
    echo "Build finished but $ZIP not found" >&2
    exit 1
  fi
  ls -la "$ZIP"
  echo "Build OK: $ZIP"
}

find_pinedfu() {
  # Prefer host venv with bleak
  local py="${ROOT}/.venv-dfu/bin/python"
  if [[ ! -x "$py" ]]; then
    echo "Missing $py — create with: python3 -m venv .venv-dfu && .venv-dfu/bin/pip install bleak pexpect" >&2
    exit 1
  fi
  if [[ ! -f "${ROOT}/tools/bleak_legacy_dfu.py" ]]; then
    echo "Missing tools/bleak_legacy_dfu.py" >&2
    exit 1
  fi

  echo "Scanning for PineDFU (put watch in OTA: hold button ~5s)..." >&2
  "$py" - <<'PY'
import asyncio
import sys
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover(timeout=15.0)
    for d in devices:
        n = (d.name or "").lower()
        if "pinedfu" in n or n.endswith("dfu"):
            print(d.address)
            return 0
    # fallback: any name containing dfu
    for d in devices:
        n = (d.name or "").lower()
        if "dfu" in n:
            print(d.address)
            return 0
    return 1

sys.exit(asyncio.run(main()))
PY
}

do_flash() {
  if [[ ! -f "$ZIP" ]]; then
    echo "No zip at $ZIP — run: $0 build" >&2
    exit 1
  fi

  local mac="${WASP_DFU_MAC:-}"
  if [[ -z "$mac" ]]; then
    mac="$(find_pinedfu)" || {
      echo "PineDFU not found. Hold the side button until OTA/bootloader UI, phone BT off, try again." >&2
      echo "Or set WASP_DFU_MAC=AA:BB:CC:DD:EE:FF" >&2
      exit 1
    }
  fi

  echo "=== OTA $ZIP → $mac ==="
  "${ROOT}/.venv-dfu/bin/python" "${ROOT}/tools/bleak_legacy_dfu.py" \
    -z "$ZIP" \
    -a "$mac" \
    --prn 10
  echo "OTA finished. Watch should reboot into the new firmware."
}

do_shell() {
  echo "Interactive build container (project mounted at /project)"
  podman run --rm -it \
    --name wasp-build-shell \
    --volume="${ROOT}:/project/:z" \
    --userns=keep-id \
    --user="$(id -u):$(id -g)" \
    --net=host \
    --entrypoint="" \
    "$IMAGE" \
    bash -lc 'cd /project && exec bash'
}

case "$CMD" in
  build) do_build ;;
  flash) do_flash ;;
  all)
    do_build
    do_flash
    ;;
  shell) do_shell ;;
  -h|--help|help)
    sed -n '2,20p' "$0"
    ;;
  *)
    echo "Unknown command: $CMD (use build|flash|all|shell)" >&2
    exit 1
    ;;
esac
