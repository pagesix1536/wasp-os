# AGENTS.md — wasp-os (Pine64 PineTime)

Project rules for AI agents and humans working in this repository.

## What this project is

**wasp-os** (Watch Application System in Python) is open-source firmware for nRF52-based smart watches. This clone is used primarily with a **Pine64 PineTime** (`BOARD=pinetime`).

- Apps and the OS shell are written in **MicroPython** (Python 3 dialect, constrained RAM/flash).
- Display is **240×240 RGB565** (ST7789 on PineTime).
- Updates and REPL access use **Bluetooth Low Energy** (Nordic UART / OTA DFU).
- Upstream (GitHub): https://github.com/wasp-os/wasp-os  
- Docs: https://wasp-os.readthedocs.io  
- App guide: https://wasp-os.readthedocs.io/en/latest/appguide.html  
- Install guide: https://wasp-os.readthedocs.io/en/latest/install.html  

## This fork (cmiller / GitHub)

This working tree is a **personal fork** for local development. Push day-to-day work to the personal GitHub remote; pull official wasp-os updates from `upstream` only.

| Remote | URL | Role |
|--------|-----|------|
| `origin` | `git@github.com:pagesix1536/wasp-os.git` | Personal GitHub fork (push here) |
| `upstream` | `https://github.com/wasp-os/wasp-os.git` | Official wasp-os (fetch / merge only) |

```sh
git push                  # → origin (GitHub: pagesix1536/wasp-os)
git fetch upstream
git merge upstream/master # when pulling official updates
```

`AGENTS.md` is **intentionally tracked on this fork** (not upstream) so agents always have project constitution/context.

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
| `docs/fork/` | **Fork Markdown** (overview, tooling, apps) — not Sphinx |
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

**Docker / Nix:** `make build-docker-image` + `make run-docker-image`, or `nix-shell tools/nix/shell.nix` — see `docs/install.rst`. The project Docker image is a **specialized wasp toolchain** (Ubuntu 24.04: Arm GCC, SDL2, Python deps, optional BLE helpers). Source is bind-mounted; tools live in the image. It is **not** the same as `~/git/grok-dev-env` (generic Grok AI shell).

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
| `README.rst` | Intro, getting started, community (upstream stock) |
| `docs/fork/README.md` | **This fork**: remotes, intent, quick start (Markdown) |
| `docs/fork/tooling.md` | Helper scripts: Podman sim, build/flash, bleak DFU |
| `docs/fork/apps.md` | Enabled apps (`wasp.toml`) + starter for new apps |
| `docs/fork/operations.md` | **Ops playbook**: --exec, OTA, boot/heap gotchas, BLE debug |
| `AGENTS.md` | This file — agent/human project constitution |
| `docs/install.rst` | Build, flash, prerequisites (upstream Sphinx) |
| `docs/appguide.rst` | Writing apps (lifecycle, APIs) |
| `docs/contributing.rst` | Style, DCO, review process |
| `docs/wasp.rst` | Reference / API |
| `TODO.rst` / `docs/TODO.rst` | Roadmap |

Fork-specific documentation is **Markdown under `docs/fork/`** only (not wired into Sphinx/Read the Docs). Prefer that tree over editing upstream RST.

## Workspace goals & environment (owner decisions)

These are **local policy** for this fork / laptop setup. Prefer them over inventing a new workflow.

### Near-term goal

- Write and iterate on **new optional Python apps** for the PineTime (under `apps/`, enable via `wasp.toml`), using the **simulator** heavily before any on-device flash.

### Host OS

- Primary laptop: **Fedora** (current; e.g. Fedora 44+), often **Wayland**.
- Official wasp release tags are old (~2021); this tree tracks **current git** (with occasional upstream activity). Still treat the project as **toolchain-sensitive** (MicroPython, SoftDevice, SDL sim).

### Active PineTime (on-device work)

Owner has multiple PineTimes; **only this one** is the development target unless they say otherwise:

| Item | Value |
|------|--------|
| BLE address | Prefer **re-scan** (random; changes with firmware). Was `…:7D` on InfiniTime; **PineDFU** was `…:7E` after reloader |
| Firmware | **git master build** (`build-pinetime/micropython.zip`, OTA 2026-08-13) — supersedes stock 0.4.1 OS image |
| Prior OS | InfiniTime 1.15.0 → stock wasp 0.4.1 → current-tree micropython |
| Bootloader | **wasp-bootloader** (via official `reloader-mcuboot.zip` 0.4.1; not re-flashed on master OTA) |
| wasptool hint | Re-scan for device name; pass `--device` / MAC. Needs `tools/pynus` submodule |

**OTA tooling note:** Phone Gadgetbridge flaky for this unit. Prefer `tools/bleak_legacy_dfu.py` + `.venv-dfu` (bleak). Stock `tools/ota-dfu` (gatttool) is unreliable on modern Fedora BlueZ. Zips for stock install live under `firmware-recovery/` (gitignored if preferred; local only).

Other watches may exist in the house; keep them distant/off so scans stay unambiguous.

### Development model (host + one project container)

Grok runs **on the host OS** (not inside a generic coding container). That gives the agent real visibility into host XWayland/display, Bluetooth, Podman, and the ability to start project containers.

| Activity | Where |
|----------|--------|
| Edit MicroPython apps (NeoVIM + Grok), design, review, git → GitHub | **Host OS** |
| `make sim`, `make check`, board firmware builds | **Project Ubuntu container only** (Podman/Docker) |
| Flash / REPL / OTA / `--rtc` | Host BLE + `wasptool`, and/or phone (Gadgetbridge) |

- **Do not** use `~/git/grok-dev-env` (or any other generic Grok/dev shell image) for this project. It is out of scope and too limiting (no useful host display/BLE/Podman control for wasp work).
- **Only** container for wasp-os: the project image from `tools/docker/` (`make build-docker-image` / `make run-docker-image`, or equivalent Podman). Use it for simulator, tests, and firmware builds — not as the editor/REPL for day-to-day coding.
- **Reason for isolation:** installing the full stack from Fedora repos risks **newer** Python / SDL / `arm-none-eabi-gcc` than the project expects; containerizing on **Ubuntu 24.04** (as in `tools/docker/Dockerfile`) reduces that skew.
- **Caveat:** the Docker image pins Ubuntu packages, **not** the historical Arm GNU-RM **10-2020-q4** binary named in the docs. If firmware builds fail in a toolchain-looking way, fall back to that official tarball before deep debugging.
- Fedora practical notes: use **Podman** (often instead of Docker CE); **SELinux** volume labels (`:z`/`:Z`); **X11/XWayland** so the SDL simulator window can appear; BLE/`wasptool` still depends on the **host** Bluetooth stack.

## Operational playbook (read this in new sessions)

Full write-up: [`docs/fork/operations.md`](docs/fork/operations.md). Summary for agents:

### Heap / “frozen” vs registered

- PineTime **64 KB RAM**; after SoftDevice + MicroPython + UI, **free heap is often only ~8–12 KB**.
- **Frozen** = code in firmware flash (cheap). **Registered** = live Python instance on the heap (costs RAM until removed + GC).
- **`--exec` + `register()`** = preferred **live test** (docs appguide). Survives until reboot only.
- **`wasp.toml` + build + OTA** = ship lasting apps. Do **not** rely on SPI `apps/foo.py` freestead + Software: frozen package `apps` only has `system`/`user`, so `import apps.foo` fails.
- `auto_load` / `quick_ring` = register at boot (always pay heap). Omit both = frozen but enable via Software when needed.
- **Step counter** is always quick-ring from core `register_defaults()` (not toml). Settings/Software always launcher.

### Commands (host BLE; one watch → omit `--device`)

```sh
# Live test (preferred while developing)
./tools/wasptool --exec apps/myapp.py --eval "wasp.system.register(MyApp())"

# REPL / heap / DFU / OTA
./tools/wasptool --console          # then wasp.system.run() after Ctrl-C
./tools/wasptool --memfree
./tools/wasptool --bootloader       # or hold side button ~5s → PineDFU
./tools/build-flash-pinetime.sh build
./tools/build-flash-pinetime.sh flash
```

SoftDevice Nordic download often **403** — helper copies from bootloader submodule. Prefer `bleak_legacy_dfu` / `build-flash-pinetime.sh`, not gatttool.

### Boot / display gotchas

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Stuck UI text **`main.py`**, no touch | `schedule()`/`register_defaults()` died: missing face dependency or **OOM** mid-autoload | Lean `auto_load`; ensure `week_clock` **and** `clock` in toml; OTA; or BLE recover |
| `ImportError: apps.user.clock` | `WeekClockApp` subclasses `ClockApp` but `clock.py` not frozen | Always list both watch faces in `wasp.toml` |
| White bg / dark glyphs / washed color | **CrashApp** left ST7789 invert wrong | Reboot, or `wasp.watch.display.invert(True)` then redraw |
| `AttributeError: sleep_at` | Half-init: `secondary_init` aborted before setting `sleep_at` | Reboot, or set `wasp.system.sleep_at = wasp.watch.rtc.uptime + 90` then `schedule()` |
| `--exec` `MemoryError` | Not enough contiguous heap to paste-compile | Reboot; disable auto-load apps; free launcher instances; or freeze |

### BLE / Gadgetbridge expectations

- wasp ≈ **NUS-centric** (few GATT services). InfiniTime exposes many more — GB icons stay thin on wasp.
- Music **transport** often works; **track metadata / weather refresh** phone→watch is flaky — don’t treat as reliable.
- Keep other house watches powered off during scans.

### Simulator

Owner interactive session: `./tools/run-sim-podman.sh` (X11/XWayland). Tab or click the left bezel ≈ side button. Press **`s`** to write `res/{App.NAME}App.png` (always that name — rename immediately if you need to keep more than one shot).

**Agents can and should drive the simulator themselves** for UI work (verified 2026-08-19). Do not skip screenshots because an interactive SDL window is awkward. Import wasp in the **project Podman image** with host `DISPLAY` and X11, `switch()` to the app, draw the page you care about, then call `display.save_image()` (same helper the `s` key uses). Do **not** call `wasp.system.run()` in that script — it is the blocking event loop. Use `secondary_init()` + `switch()` + save, then exit.

```sh
# Host: allow the container to talk to XWayland
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
  bash -lc 'cd /project && PYTHONPATH=.:wasp/boards/simulator:wasp:wasp/apps/system python3 script.py'
```

In `script.py`: `import wasp`, `import display`, `wasp.system.secondary_init()`, construct or `switch()` the app, set `app.page` / inject state, `wasp.system.switch(app)`, `display.window.refresh()`, then `display.save_image(display.windowsurface, "res/Whatever.png")`. Pick a **distinct** filename; `s` and `{NAME}App.png` overwrite.

Other sim facts:

- `make check` / unit tests can use `SDL_VIDEODRIVER=dummy` (no window). Screenshots need real X11 as above.
- Enabled apps are **copied** to `wasp/apps/user/` from `wasp.toml`. After editing `apps/*.py`, `cp` into `wasp/apps/user/` (or re-run `tools/configure_wasp_apps.py wasp.toml`) before sim/import, or you will screenshot stale code.
- Import the tree you just edited (`from apps.alarm import AlarmApp`) when the script constructs the app; the registered quick-ring instance may still be the `apps.user` copy.
- Headless pytest that imports every `watch_faces/*.py` currently dies on this fork (`week_clock` wants `apps.user.clock`, which is not frozen). That is pre-existing; do not treat it as a regression in the app you are changing.
- Free-RAM display is often **Not supported** in sim.
- An **interactive** `make sim` window the agent launches can still steal/freeze host input. Prefer a short script + `save_image` for agent verification; leave the long-lived window to the owner.

### Tracking ideas

- Use **GitHub Issues** on this fork (e.g. US 12h face: issue #1). Labels like `enhancement` / `bug`. Skip Projects/Milestones unless asked.

## Agent working notes

- Default device context is **PineTime** (`BOARD=pinetime`).
- Prefer **`--exec` for on-watch app iteration**; simulator for UI layout; **OTA freeze** when shipping.
- Prefer **simulator + `make check`** over flashing for everyday Python UI work when hardware isn’t needed.
- After a UI change, **drive the sim and save a screenshot** (see Simulator above). Do not stop at “it compiled” or a hand-drawn mockup.
- Custom feature sets go through **`wasp.toml`**, not hard-coding every app into the board manifest by hand.
- Core OS changes touch `wasp/`, drivers, and/or board `watch.py.in` / manifests; optional apps usually stay under `apps/` or `watch_faces/`.
- Do not treat experimental Grok cross-session memory as a substitute for this file or `docs/fork/`; keep durable project facts here.
- Official docs site may be more polished than in-tree RST; when they disagree on install steps, prefer `docs/install.rst` for this tree — but prefer **`docs/fork/`** for fork ops.
- Prefer SSH for `origin` (`git@github.com:pagesix1536/wasp-os.git`).
- Setup focus: **host Podman + project Ubuntu image** for `make check` / `make sim` / firmware builds. Edit on the host; never route wasp workflow through grok-dev-env.
