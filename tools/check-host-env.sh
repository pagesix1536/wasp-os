#!/usr/bin/env bash
# Print a host-environment checklist for wasp-os sim / firmware / OTA.
# Read-only; does not install packages.
set -euo pipefail

ok() { printf '  OK    %s\n' "$*"; }
miss() { printf '  MISS  %s\n' "$*"; }
info() { printf '  INFO  %s\n' "$*"; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=wasp-engine.sh
source "$ROOT/tools/wasp-engine.sh"

echo "Host"
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  info "os=${PRETTY_NAME:-$NAME} id=${ID:-?} like=${ID_LIKE:-?}"
fi
info "kernel=$(uname -r) session=${XDG_SESSION_TYPE:-?} desktop=${XDG_CURRENT_DESKTOP:-?}"
info "python=$(python3 --version 2>/dev/null | awk '{print $2}')"

echo "Container engine (builds + simulator)"
if command -v podman >/dev/null 2>&1; then
  ok "podman $(podman --version 2>/dev/null | awk '{print $3}')"
else
  miss "podman  (omarchy pkg add podman fuse-overlayfs)"
fi
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    info "docker CLI works without sudo (not required for this workflow)"
  else
    info "docker is installed but not usable without sudo (Omarchy default; ignore)"
  fi
fi
IMAGE="${WASP_DEV_IMAGE:-wasp-os/wasp-os-dev:0.1.0}"
if command -v podman >/dev/null 2>&1 && wasp_image_exists podman "$IMAGE"; then
  ok "image $IMAGE"
else
  miss "image $IMAGE  (./tools/build-dev-image.sh)"
fi

echo "Simulator display"
if [[ -n "${DISPLAY:-}" ]]; then
  ok "DISPLAY=${DISPLAY}"
else
  miss "DISPLAY (need an X11/XWayland session)"
fi
if [[ -S /tmp/.X11-unix/X0 || -S /tmp/.X11-unix/X1 ]]; then
  ok "X11 unix socket in /tmp/.X11-unix"
else
  miss "X11 unix socket (Hyprland XWayland not running?)"
fi
if command -v xhost >/dev/null 2>&1; then
  ok "xhost (xorg-xhost)"
else
  miss "xhost  (omarchy pkg add xorg-xhost)"
fi

echo "Host BLE (wasptool / OTA; not inside the container)"
if systemctl is-active --quiet bluetooth 2>/dev/null; then
  ok "bluetooth.service active"
else
  miss "bluetooth.service"
fi
if python3 -c "import pexpect" >/dev/null 2>&1; then
  ok "python3 pexpect (wasptool)"
else
  miss "python3 pexpect  (omarchy pkg add python-pexpect)"
fi
if python3 -c "import bleak" >/dev/null 2>&1; then
  ok "python3 bleak (DFU)"
elif [[ -x "$ROOT/.venv-dfu/bin/python" ]] && "$ROOT/.venv-dfu/bin/python" -c "import bleak" >/dev/null 2>&1; then
  ok ".venv-dfu bleak"
else
  miss "bleak  (omarchy pkg add python-bleak  or  .venv-dfu)"
fi
if python3 -c "import dbus, gi.repository.GLib" >/dev/null 2>&1; then
  ok "python3 dbus + GLib (pynus/tealblue)"
else
  miss "python3 dbus/GLib  (python-dbus python-gobject)"
fi
if [[ -f "$ROOT/tools/pynus/pynus.py" ]]; then
  ok "tools/pynus submodule"
else
  miss "tools/pynus  (git submodule update --init)"
fi

echo "Firmware sources"
if [[ -f "$ROOT/micropython/ports/nrf/Makefile" ]]; then
  ok "micropython submodule"
else
  miss "micropython submodule  (git submodule update --init)"
fi
if [[ -d "$ROOT/bootloader/lib/softdevice" ]] || [[ -f "$ROOT/micropython/ports/nrf/drivers/bluetooth/s132_nrf52_6.1.1/s132_nrf52_6.1.1_softdevice.hex" ]]; then
  ok "SoftDevice tree present or copyable"
else
  info "SoftDevice hex not on disk yet (build helper copies from bootloader after submodules)"
fi

echo "Done. MISS items block sim, firmware build, and/or flashing."
