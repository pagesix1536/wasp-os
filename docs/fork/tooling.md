# Helper tooling (this fork)

Scripts and workflows added for day-to-day PineTime work on **Omarchy (Arch + Hyprland) + rootless Podman + host Bluetooth**. The same helpers still work on Fedora if Podman and SELinux volume labels are present. Stock wasp tools (`wasptool`, Makefile targets, Docker image) remain available; these helpers paper over host-distro skew, X11/XWayland, SoftDevice download issues, and unreliable gatttool DFU on modern BlueZ.

After a fresh OS install, run `./tools/check-host-env.sh` to see what is missing.

## Overview

| Tool | Role |
|------|------|
| [`tools/check-host-env.sh`](../../tools/check-host-env.sh) | Read-only checklist (podman, image, X11, BLE Python, submodules) |
| [`tools/build-dev-image.sh`](../../tools/build-dev-image.sh) | Build `wasp-os/wasp-os-dev:0.1.0` with rootless podman |
| [`tools/run-sim-podman.sh`](../../tools/run-sim-podman.sh) | Launch SDL simulator in the project image with working X11 |
| [`tools/sim_smoke_screenshot.py`](../../tools/sim_smoke_screenshot.py) | One-shot sim init + PNG (no event loop) |
| [`tools/screenshot_battery_meter.py`](../../tools/screenshot_battery_meter.py) | Force sim battery level/charging and save status-bar shots |
| [`tools/build-flash-pinetime.sh`](../../tools/build-flash-pinetime.sh) | Build `build-pinetime/micropython.zip` and/or OTA flash |
| [`tools/bleak_legacy_dfu.py`](../../tools/bleak_legacy_dfu.py) | Nordic legacy DFU client (bleak), used by the flash helper |
| [`tools/wasptool`](../../tools/wasptool) | Stock BLE REPL / RTC / file transfer (host; needs `tools/pynus`) |
| [`tools/wasp-engine.sh`](../../tools/wasp-engine.sh) | Shared podman flags (sourced; not run directly) |

### GitHub Actions on this fork

| Workflow | Status on this fork |
|----------|---------------------|
| `.github/workflows/main.yml` (binary distribution) | **Disabled** — SoftDevice Nordic download fails in CI (403); multi-board dist not needed for PineTime-only local builds. File kept for later re-enable (see comments in the workflow). |
| `.github/workflows/sim.yml` (simulator tests) | **Disabled** — local Podman sim already covers this; CI was red noise (`week_clock` → missing `apps.user.clock`). File kept for later re-enable. |

Environment overrides used by the helpers:

| Variable | Default | Meaning |
|----------|---------|---------|
| `WASP_DEV_IMAGE` | `wasp-os/wasp-os-dev:0.1.0` | Podman image name |
| `WASP_MPY_ZIP` | `build-pinetime/micropython.zip` | OTA zip path |
| `WASP_DFU_MAC` | *(auto-scan PineDFU)* | Force DFU MAC address |
| `BOARD` | `pinetime` | Make board for builds |
| `WASP_SIM_NAME` | `wasp-sim` | Container name for the simulator |

---

## Host packages (Omarchy)

Omarchy already has Docker, but the daemon is **sudo-only** (the `docker` group is treated as passwordless root). Do **not** enable sudoless Docker for this project. Install rootless Podman and the host BLE/X11 bits:

```sh
omarchy pkg add podman fuse-overlayfs xorg-xhost python-pexpect python-bleak
git submodule update --init
./tools/check-host-env.sh
```

`python-dbus` and `python-gobject` (pynus/tealblue) are typically already installed. `wasptool` is `#!/usr/bin/env python3` — it needs **system** `pexpect`, not only a venv.

## Project container image

Builds and the simulator run **inside** the image from `tools/docker/`, not on the host toolchain.

```sh
./tools/build-dev-image.sh
# → wasp-os/wasp-os-dev:0.1.0
```

`make build-docker-image` (upstream) runs `docker compose` and will fail on Omarchy with `permission denied` on `/var/run/docker.sock`. Use the podman helper.

Notes:

- Prefer **rootless Podman**. Helpers never `sudo docker`.
- Source is bind-mounted at `/project`. SELinux `:z` and `label=disable` are added **only** when `/sys/fs/selinux/enforce` exists (Fedora). Omarchy has no SELinux.
- Simulator needs **X11/XWayland** (`DISPLAY`, `/tmp/.X11-unix`). Hyprland on this laptop runs XWayland as `:0`.
- Use `--userns=keep-id` so files written on the mount match the host user.
- BLE/OTA stays on the **host** stack; the container is for compile + sim only.

---

## Simulator: `run-sim-podman.sh`

```sh
./tools/run-sim-podman.sh
```

What it does:

1. Checks that `WASP_DEV_IMAGE` exists and `DISPLAY` is set.
2. Runs `xhost +local:` when available (XWayland clients).
3. Starts an interactive container with:
   - project mount, X11 socket, `SDL_VIDEODRIVER=x11`
   - `label=disable`, `keep-id`, host network
   - entrypoint: `make sim`

Simulator input (host):

- **Tab** or click the **left edge** ≈ side button
- Touch / swipe as on the device (mouse)

Stop: close the SDL window or Ctrl+C in the terminal.

One-shot screenshot (no event loop; good for agents and X11 smoke tests):

```sh
./tools/run-sim-podman.sh   # interactive
# or:
podman run --rm --volume="$PWD:/project/" --volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
  --env=DISPLAY="${DISPLAY}" --env=SDL_VIDEODRIVER=x11 \
  --userns=keep-id --user="$(id -u):$(id -g)" --net=host --entrypoint="" \
  "${WASP_DEV_IMAGE:-wasp-os/wasp-os-dev:0.1.0}" \
  bash -lc 'cd /project && PYTHONPATH=.:wasp/boards/simulator:wasp:wasp/apps/system python3 tools/sim_smoke_screenshot.py'
```

### Forced battery-meter screenshots

The simulator’s `Battery` class wanders voltage over time. To pin level/charging and dump PNGs (issue #3):

```sh
xhost +local: >/dev/null 2>&1 || true
podman run --rm \
  --volume="$PWD:/project/" \
  --volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
  --env=DISPLAY="${DISPLAY}" \
  --env=SDL_VIDEODRIVER=x11 \
  --userns=keep-id --user="$(id -u):$(id -g)" --net=host \
  --entrypoint="" \
  "${WASP_DEV_IMAGE:-wasp-os/wasp-os-dev:0.1.0}" \
  bash -lc 'cd /project && PYTHONPATH=.:wasp/boards/simulator:wasp:wasp/apps/system python3 tools/screenshot_battery_meter.py'
```

Writes `/tmp/wasp-battery-meter/battery-meter-*.png` (full sim skin) so shots do not clutter `res/` with UI icons. Meter behavior is documented in [operations.md](operations.md#status-bar-battery-meter-issue-3).

If the image is missing:

```sh
./tools/build-dev-image.sh
```

---

## Build + flash: `build-flash-pinetime.sh`

```sh
./tools/build-flash-pinetime.sh build   # only build micropython.zip
./tools/build-flash-pinetime.sh flash   # only OTA existing zip
./tools/build-flash-pinetime.sh all     # build then flash (default)
./tools/build-flash-pinetime.sh shell   # interactive build container
```

### Build path

1. Ensures SoftDevice **s132_nrf52_6.1.1** is present under the MicroPython nRF port.
   - Nordic’s direct download often returns **HTTP 403**.
   - Helper copies from the bootloader submodule tree when needed.
2. Runs `make -j$(nproc) BOARD=pinetime micropython` inside Podman.
3. App set comes from root [`wasp.toml`](../../wasp.toml) (regenerated into manifests on build).
4. Output: `build-pinetime/micropython.zip` (and related artifacts under `build-pinetime/`).

First-time submodule init can be slow; subsequent builds are incremental.

### Flash path (OTA)

Prerequisites on the **host**: `python3` that can `import bleak` — either the distro package or a venv:

```sh
# Omarchy (preferred)
omarchy pkg add python-bleak python-pexpect

# Optional venv instead (any distro)
python3 -m venv .venv-dfu
.venv-dfu/bin/pip install bleak pexpect
```

On the watch:

1. Hold the **side button ~5 seconds** until OTA / bootloader UI (**PineDFU** advertising name after reloader install).
2. Turn **phone Bluetooth off** (or keep other phones away) so the DFU connection is not stolen.
3. Run:

```sh
./tools/build-flash-pinetime.sh flash
# or force MAC:
WASP_DFU_MAC=AA:BB:CC:DD:EE:FF ./tools/build-flash-pinetime.sh flash
```

The script scans for a device whose name contains `pinedfu` / `dfu`, then runs `bleak_legacy_dfu.py` with PRN 10.

**Phone Gadgetbridge** OTA has been flaky for this setup; prefer the Linux bleak path.

### SoftDevice note

If SoftDevice is still missing after a failed Nordic download:

```sh
# submodules include bootloader SoftDevice copy used by the helper
make submodules   # or via: ./tools/build-flash-pinetime.sh build
```

---

## DFU client: `bleak_legacy_dfu.py`

Nordic **legacy DFU** (SDK ≤ 11 style) over [bleak](https://github.com/hbldh/bleak). Mirrors the protocol of stock `tools/ota-dfu` (gatttool), which often fails GATT discovery on modern BlueZ.

Typical direct use:

```sh
.venv-dfu/bin/python tools/bleak_legacy_dfu.py \
  -z build-pinetime/micropython.zip \
  -a AA:BB:CC:DD:EE:FF \
  --prn 10
```

Useful for:

- InfiniTime → reloader / recovery zips (when those use legacy DFU)
- PineDFU → `micropython.zip` after wasp bootloader is installed

Recovery zips (stock 0.4.1 reloader, etc.) may live under a local `firmware-recovery/` directory (often gitignored). Prefer known-good **official** bootloader packages on a sealed PineTime; a bad bootloader without SWD can brick the watch.

---

## wasptool (stock, host BLE)

After the watch is running wasp micropython (not only PineDFU):

```sh
./tools/wasptool --console     # MicroPython REPL
./tools/wasptool --rtc         # set clock from host
./tools/wasptool --battery
./tools/wasptool --upload apps/my_app.py
./tools/wasptool --bootloader  # reboot into OTA mode
./tools/wasptool --reset
```

BLE addresses/names are often **random**; re-scan and pass `--device` / MAC when needed. Submodule `tools/pynus` must be present.

After `Ctrl+C` into the REPL, resume the UI with:

```python
wasp.system.run()
```

---

## Tests and firmware (reference)

| Goal | Command |
|------|---------|
| Simulator pytest | In container: `make check` (this fork still fails collection on `week_clock` → missing `apps.user.clock`; pre-existing) |
| Interactive sim | `./tools/run-sim-podman.sh` |
| Full board tree | Container: `make -j$(nproc) BOARD=pinetime all` |
| Micropython zip only | `./tools/build-flash-pinetime.sh build` |

Free memory on device (when relevant):

```sh
./tools/wasptool --memfree
```

---

## Troubleshooting

| Symptom | Likely fix |
|---------|------------|
| Sim: no window / permission on `/tmp/.X11-unix` | Use `run-sim-podman.sh` (not stock docker run); Hyprland needs XWayland/`DISPLAY`; install `xorg-xhost` |
| Sim: image not found | `./tools/build-dev-image.sh` |
| `docker` permission denied on Omarchy | Expected — do not join the docker group; use podman |
| `wasptool` `ModuleNotFoundError: pexpect` | `omarchy pkg add python-pexpect` (shebang is system python3) |
| Build: SoftDevice / 403 | Let the flash helper copy from bootloader; `make submodules` |
| OTA: PineDFU not found | Hold button longer; phone BT off; set `WASP_DFU_MAC` |
| OTA: gatttool/`ota-dfu` fails | Use `bleak_legacy_dfu.py` / `build-flash-pinetime.sh flash` |
| wasptool cannot connect | Re-scan; wrong watch nearby; leave PineDFU and boot full firmware |

See also [README.md](README.md) for remotes and intent, and [apps.md](apps.md) for the enabled app set.
