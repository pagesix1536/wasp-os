# Helper tooling (this fork)

Scripts and workflows added for day-to-day PineTime work on **Fedora + Podman + host Bluetooth**. Stock wasp tools (`wasptool`, Makefile targets, Docker image) remain available; these helpers paper over SELinux/X11, SoftDevice download issues, and unreliable gatttool DFU on modern BlueZ.

## Overview

| Tool | Role |
|------|------|
| [`tools/run-sim-podman.sh`](../../tools/run-sim-podman.sh) | Launch SDL simulator in the project image with working X11 |
| [`tools/screenshot_battery_meter.py`](../../tools/screenshot_battery_meter.py) | Force sim battery level/charging and save status-bar shots |
| [`tools/build-flash-pinetime.sh`](../../tools/build-flash-pinetime.sh) | Build `build-pinetime/micropython.zip` and/or OTA flash |
| [`tools/bleak_legacy_dfu.py`](../../tools/bleak_legacy_dfu.py) | Nordic legacy DFU client (bleak), used by the flash helper |
| [`tools/wasptool`](../../tools/wasptool) | Stock BLE REPL / RTC / file transfer (host; needs `tools/pynus`) |
| `make build-docker-image` | Build `wasp-os/wasp-os-dev:0.1.0` (Ubuntu 24.04 toolchain) |

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

## Project container image

Builds and the simulator run **inside** the image from `tools/docker/`, not on the host toolchain.

```sh
make build-docker-image
# → wasp-os/wasp-os-dev:0.1.0
```

Notes for Fedora/Podman:

- Prefer **Podman** over Docker CE.
- Source is bind-mounted with SELinux `:z` (`/project/:z`).
- Simulator needs **X11/XWayland** (`DISPLAY`, `/tmp/.X11-unix`) and typically `--security-opt label=disable` so SDL can open the socket (stock `make run-docker-image` is not enough here).
- Use `--userns=keep-id` so files written on the mount match the host user (avoid `--userns=host` for this workflow).
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

### Forced battery-meter screenshots

The simulator’s `Battery` class wanders voltage over time. To pin level/charging and dump PNGs (issue #3):

```sh
xhost +local: >/dev/null 2>&1 || true
podman run --rm \
  --security-opt label=disable \
  --volume="$PWD:/project/:z" \
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
make build-docker-image
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

Prerequisites on the **host**:

```sh
python3 -m venv .venv-dfu
.venv-dfu/bin/pip install bleak pexpect
# tools/bleak_legacy_dfu.py is already in the tree
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

Nordic **legacy DFU** (SDK ≤ 11 style) over [bleak](https://github.com/hbldh/bleak). Mirrors the protocol of stock `tools/ota-dfu` (gatttool), which often fails GATT discovery on modern Fedora BlueZ.

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
| Simulator pytest | In container: `make check` |
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
| Sim: no window / permission on `/tmp/.X11-unix` | Use `run-sim-podman.sh` (not stock docker run); ensure Wayland session has XWayland/`DISPLAY` |
| Sim: image not found | `make build-docker-image` |
| Build: SoftDevice / 403 | Let the flash helper copy from bootloader; `make submodules` |
| OTA: PineDFU not found | Hold button longer; phone BT off; set `WASP_DFU_MAC` |
| OTA: gatttool/`ota-dfu` fails | Use `bleak_legacy_dfu.py` / `build-flash-pinetime.sh flash` |
| wasptool cannot connect | Re-scan; wrong watch nearby; leave PineDFU and boot full firmware |

See also [README.md](README.md) for remotes and intent, and [apps.md](apps.md) for the enabled app set.
