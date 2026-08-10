# AGENTS.md — wasp-os (Pine64 PineTime)

Project rules for AI agents and humans working in this repository.

## What this project is

**wasp-os** (Watch Application System in Python) is open-source firmware for nRF52-based smart watches. This clone is used primarily with a **Pine64 PineTime** (`BOARD=pinetime`).

- Apps and the OS shell are written in **MicroPython** (Python 3 dialect, constrained RAM/flash).
- Display is **240×240 RGB565** (ST7789 on PineTime).
- Updates and REPL access use **Bluetooth Low Energy** (Nordic UART / OTA DFU).
- Upstream: https://github.com/wasp-os/wasp-os  
- Docs: https://wasp-os.readthedocs.io  
- App guide: https://wasp-os.readthedocs.io/en/latest/appguide.html  
- Install guide: https://wasp-os.readthedocs.io/en/latest/install.html  

## Hardware focus (this workspace)

| Item | Value |
|------|--------|
| Primary device | Pine64 PineTime |
| Make target | `BOARD=pinetime` |
| MCU / stack | nRF52832 + SoftDevice S132 |
| Screen | 240×240, color (draw via `draw565`) |
| Sensors (PineTime) | battery, BMA421 accel/steps, CST816S touch, HRS3300 HR, vibrator, RTC |

Other boards exist (`p8`, `k9`, `dsd6`, `nitrogen`) but default assumptions here should be **PineTime** unless the user says otherwise.

## Top-level layout

| Path | Role |
|------|------|
| `apps/` | Optional / user apps and games (selected via `wasp.toml`) |
| `watch_faces/` | Clock faces (selected via `wasp.toml`) |
| `wasp/` | Core OS, widgets, drivers, board ports, system apps |
| `wasp/wasp.py` | System manager (`wasp.system`) and event model |
| `wasp/widgets.py` | Shared UI widgets |
| `wasp/draw565.py` | Drawing / framebuffer helpers |
| `wasp/drivers/` | Hardware drivers (display, touch, HR, battery, …) |
| `wasp/boards/pinetime/` | PineTime board support (`manifest.py`, `watch.py.in`) |
| `wasp/boards/simulator/` | Host simulator + pytest suite |
| `wasp/apps/system/` | Built-in system apps (launcher, settings, software, …) |
| `wasp.toml` | **Custom build config**: which apps/faces ship, quick-ring, auto-load |
| `tools/wasptool` | BLE tool: REPL, OTA, push/pull files, set RTC, battery |
| `tools/configure_wasp_apps.py` | Generates app registry from `wasp.toml` |
| `bootloader/` | Adafruit nRF52 bootloader (submodule) — OTA recovery |
| `reloader/` | Reloader / recovery image |
| `micropython/` | MicroPython port (submodule) frozen into firmware |
| `docs/` | Sphinx docs (install, app guide, contributing, API) |
| `res/` | Icons, screenshots, media |
| `build-pinetime/` | Build outputs for PineTime (after a successful build) |
| `Makefile` | Submodules, softdevice, board firmware, sim, tests, docs |

Git submodules (`bootloader`, `micropython`, etc.) must be initialized before a full device build (`make submodules`).

## Build & run (PineTime)

Prerequisites: Python 3.6+, deps from `wasp/requirements.txt` (or distro packages listed in `docs/install.rst`), and an **Arm GNU-RM** toolchain (project tested with 10-2020-q4).

```sh
# First-time setup
make submodules
make softdevice

# Full PineTime firmware (bootloader + reloader + micropython)
make -j"$(nproc)" BOARD=pinetime all
# Artifacts land in build-pinetime/
```

Useful targets:

```sh
make sim                          # interactive host simulator (no hardware)
make check                        # simulator pytest (QA + smoke); run before PRs
make docs                         # Sphinx docs → docs/build/html
make apps                         # compile optional apps to .mpy
make BOARD=pinetime clean         # clean board-specific build trees
```

**Custom app set:** edit `wasp.toml` (quick_ring, auto_load, watch faces). Regenerates manifests on the next build.

**Docker / Nix:** `make build-docker-image` + `make run-docker-image`, or `nix-shell tools/nix/shell.nix` — see `docs/install.rst`.

### Talking to a watch (wasptool)

```sh
./tools/wasptool --console          # MicroPython REPL over BLE
./tools/wasptool --rtc              # set watch time from host
./tools/wasptool --battery
./tools/wasptool --ota path/to.zip  # OTA update
./tools/wasptool --upload file.py   # copy a file to the device
./tools/wasptool --push / --pull    # filesystem transfer
./tools/wasptool --bootloader       # reboot into bootloader for OTA
./tools/wasptool --reset
```

After interrupting the watch into the REPL (`Ctrl+C`), resume the UI with `wasp.system.run()`.

**Sealed PineTime caution:** prefer official release bootloaders over untested CI bootloaders; a bad bootloader can brick a sealed watch without SWD recovery.

## Application development

Prefer the **simulator** (`make sim`) while iterating. Full guide: `docs/appguide.rst` and `apps/template.py`.

### App locations

- Optional apps: `apps/*.py` — enable in `wasp.toml`
- Watch faces: `watch_faces/*.py` — enable in `wasp.toml`
- System apps: `wasp/apps/system/`
- Templates: `apps/template.py`, `apps/hello.py` / `docs/hello.py`

### App contract (duck typing — no required base class)

| Member | Required | Purpose |
|--------|----------|---------|
| `NAME` | yes | Launcher label (keep ≤ ~8 chars if possible) |
| `ICON` | recommended | Launcher icon (≤ 96×64 RLE data) |
| `foreground()` | yes | Take over the screen; full redraw |
| `background()` | optional | Tear-down when leaving the app |
| `sleep()` / `wake()` | optional | Stay active across sleep; most apps omit |
| `preview()` | watch faces only | Used by the face picker |
| Event handlers | optional | `touch`, `swipe`, `press`, tick, … |

Typical pattern:

```python
import wasp

class HelloApp:
    NAME = "Hello"

    def foreground(self):
        self._draw()
        wasp.system.request_event(
            wasp.EventMask.TOUCH | wasp.EventMask.SWIPE_UPDOWN | wasp.EventMask.BUTTON
        )
        wasp.system.request_tick(1000)

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill()
        draw.string("Hello, world!", 0, 108, width=240)
```

### Important APIs

- `wasp.system` — manager: register events/ticks, navigate apps, notifications
- `wasp.watch` — board hardware facade (`drawable`, RTC, sensors, …)
- `wasp.EventMask` / `wasp.EventType` — touch, swipe, button events
- `widgets` — buttons, spinners, checkboxes, etc.
- Memory is tight: avoid large allocations; prefer small state and efficient redraws

Only one app is **active** at a time; backgrounded apps must remember state so they appear continuous when reopened.

## Coding conventions

- Python: **PEP 8** (same spirit as MicroPython project style).
- Keep MicroPython constraints in mind: limited heap, no full CPython stdlib, prefer simple constructs.
- Prefer editing existing patterns in nearby apps over introducing heavy frameworks.
- Do not commit generated or build trees (`build-*`, `wasp/apps/user`, `wasp/boards/*/watch.py` from preprocess, `*.mpy` under apps unless intentional).
- License headers: many files use SPDX (`LGPL-3.0-or-later` for core; respect per-file headers). New optional apps often use their own SPDX/copyright line.

### Contributions (upstream)

If preparing patches for upstream wasp-os:

1. Pass CI mentally: compile for a real board + `make check`.
2. Every commit needs **`Signed-off-by: Name <email>`** (Developer Certificate of Origin; `git commit --signoff`).
3. See `docs/contributing.rst` and the project code of conduct.

## Testing checklist

Before claiming a change is done:

1. `make check` — simulator unit/QA/smoke tests  
2. Prefer `make sim` for manual UI checks  
3. For firmware changes: `make -j"$(nproc)" BOARD=pinetime all`  
4. On device (when available): flash/OTA, smoke-test the modified app, check memory with `./tools/wasptool --memfree` if relevant  

## Docs map

| Doc | Content |
|-----|---------|
| `README.rst` | Intro, getting started, community |
| `docs/install.rst` | Build, flash, prerequisites |
| `docs/appguide.rst` | Writing apps (lifecycle, APIs) |
| `docs/contributing.rst` | Style, DCO, review process |
| `docs/wasp.rst` | Reference / API |
| `TODO.rst` / `docs/TODO.rst` | Roadmap |

## Agent working notes

- Default device context is **PineTime** (`BOARD=pinetime`).
- Prefer **simulator + `make check`** over flashing for everyday Python app work.
- Custom feature sets go through **`wasp.toml`**, not hard-coding every app into the board manifest by hand.
- Core OS changes touch `wasp/`, drivers, and/or board `watch.py.in` / manifests; optional apps usually stay under `apps/` or `watch_faces/`.
- Do not treat experimental Grok cross-session memory as a substitute for this file; keep durable project facts here or in committed docs.
- Official docs site may be more polished than in-tree RST; when they disagree on install steps, prefer `docs/install.rst` for this tree.
- Git may print `unable to write credential store: Device or resource busy` when talking to the LAN Gitea remote from this container. That is a known issue with the bind-mounted `~/.git-credentials` file; auth still works. **Safe to ignore** if the git operation otherwise succeeds.
