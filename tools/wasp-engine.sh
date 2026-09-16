#!/usr/bin/env bash
# Shared container-engine helpers for this fork's sim/build scripts.
# Source this file; do not execute it.
#
# Prefer rootless podman. Omarchy ships Docker, but the daemon is sudo-only
# by design (docker group == passwordless root). Do not fall back to sudo
# docker from these helpers.

wasp_selinux_enabled() {
  [[ -e /sys/fs/selinux/enforce ]]
}

wasp_pick_engine() {
  if [[ -n "${WASP_ENGINE:-}" ]]; then
    if ! command -v "$WASP_ENGINE" >/dev/null 2>&1; then
      echo "WASP_ENGINE=$WASP_ENGINE not found on PATH" >&2
      return 1
    fi
    printf '%s\n' "$WASP_ENGINE"
    return 0
  fi
  if command -v podman >/dev/null 2>&1; then
    printf '%s\n' podman
    return 0
  fi
  echo "podman not found. This workflow uses rootless podman (not Omarchy's sudo-only Docker)." >&2
  echo "Install: omarchy pkg add podman xorg-xhost python-pexpect python-bleak fuse-overlayfs" >&2
  echo "Fedora:  sudo dnf install podman xorg-x11-server-utils python3-pexpect python3-bleak" >&2
  return 1
}

wasp_image_exists() {
  local engine="$1" image="$2"
  case "$engine" in
    podman) podman image exists "$image" ;;
    docker) docker image inspect "$image" >/dev/null 2>&1 ;;
    *) return 1 ;;
  esac
}

# Append project-mount / UID-map flags to the named array.
# wasp_fill_project_args ARRAY_NAME engine root
wasp_fill_project_args() {
  local -n _wasp_args=$1
  local engine="$2"
  local root="$3"
  local vol="${root}:/project"

  if wasp_selinux_enabled; then
    vol="${vol}:z"
    _wasp_args+=(--security-opt=label=disable)
  fi
  _wasp_args+=(--volume="$vol")
  _wasp_args+=(--user="$(id -u):$(id -g)")
  _wasp_args+=(--net=host)
  _wasp_args+=(--entrypoint="")
  if [[ "$engine" == podman ]]; then
    _wasp_args+=(--userns=keep-id)
  fi
}

# Append X11 / SDL flags. Needs DISPLAY (XWayland on Hyprland/Omarchy).
wasp_fill_x11_args() {
  local -n _wasp_x11=$1
  if [[ -z "${DISPLAY:-}" ]]; then
    echo "DISPLAY is not set; cannot open an SDL window." >&2
    echo "On Omarchy/Hyprland, XWayland should set DISPLAY=:0 in a graphical session." >&2
    return 1
  fi
  if command -v xhost >/dev/null 2>&1; then
    xhost +local: >/dev/null 2>&1 || true
  fi
  _wasp_x11+=(--volume=/tmp/.X11-unix:/tmp/.X11-unix:rw)
  _wasp_x11+=(--env=DISPLAY="${DISPLAY}")
  _wasp_x11+=(--env=SDL_VIDEODRIVER=x11)
  if [[ -n "${XAUTHORITY:-}" && -r "${XAUTHORITY}" ]]; then
    _wasp_x11+=(--volume="${XAUTHORITY}:${XAUTHORITY}:ro")
    _wasp_x11+=(--env=XAUTHORITY="${XAUTHORITY}")
  fi
}

# Python that can import bleak (DFU / PineDFU scan).
wasp_dfu_python() {
  local root="$1"
  local py
  if [[ -n "${WASP_DFU_PYTHON:-}" ]]; then
    printf '%s\n' "$WASP_DFU_PYTHON"
    return 0
  fi
  if [[ -x "${root}/.venv-dfu/bin/python" ]]; then
    py="${root}/.venv-dfu/bin/python"
  else
    py="python3"
  fi
  if ! "$py" -c "import bleak" >/dev/null 2>&1; then
    echo "bleak is not importable from $py." >&2
    echo "Omarchy: omarchy pkg add python-bleak python-pexpect" >&2
    echo "Or: python3 -m venv .venv-dfu && .venv-dfu/bin/pip install bleak pexpect" >&2
    return 1
  fi
  printf '%s\n' "$py"
}
