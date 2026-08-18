# Apps on this fork

Notes for optional apps and watch faces shipped in **this** PineTime build. Upstream still has the full app guide in Sphinx (`docs/appguide.rst`); use this file as the fork’s living list and a short starter for new work.

App selection is controlled by root [`wasp.toml`](../../wasp.toml). Nothing under `apps/` is frozen into firmware until it is listed there and you rebuild / OTA.

---

## Currently enabled (`wasp.toml`)

### Quick ring (swipe left/right from the clock)

| File | Notes |
|------|--------|
| `apps/alarm.py` | Quick-ring |
| `apps/timer.py` | Quick-ring |
| *(system)* Step counter | Always registered by core — not in `wasp.toml` |

### Auto-loaded (launcher after boot)

| File | Notes |
|------|--------|
| `apps/heart.py` | HR; HRS3300 on device |
| `apps/weather.py` | Gadgetbridge weather (phone→watch refresh flaky) |
| `apps/music_player.py` | Gadgetbridge music controls (metadata flaky) |

### Frozen, enable in Software when wanted

| File | Notes |
|------|--------|
| `apps/memory.py` | Free RAM (Boot/Init/Now/GC); prefer `--exec` while iterating |

System apps **Settings** and **Software** always appear on the launcher.

### Watch faces

| File | Default? |
|------|----------|
| `watch_faces/clock_us.py` | **Yes** — US 12h + `Wed, Aug 13` date (issue #1); sole face |

Stock `clock.py` / `week_clock.py` are not frozen. The Faces picker (`apps/faces.py`) is also not enabled — with only one face there is nothing to switch.

Quick on-device test without rebuild:

```sh
./tools/wasptool --exec apps/memory.py --eval "wasp.system.register(MemoryApp())"
```

---

## Apps available in-tree but not enabled

Many other optional apps live under `apps/` (games, sports, morse, pomodoro, …). To enable one:

1. Add an `[[app]]` block in `wasp.toml` (see examples below).
2. Rebuild and OTA (or push a single `.py` for quick experiments).

```toml
[[app]]
file = 'apps/snake.py'
# quick_ring = true   # optional
# auto_load = true    # optional
```

Flash is limited; only enable what you will use.

---

## Starter: writing a new app

### Where files go

| Kind | Path | Register in |
|------|------|-------------|
| Optional app | `apps/my_thing.py` | `wasp.toml` `[[app]]` |
| Watch face | `watch_faces/my_face.py` | `wasp.toml` `[[watchface]]` |
| System app | `wasp/apps/system/` | Board manifests (core OS; usually avoid) |

Templates in-tree:

- `apps/template.py` — fuller skeleton with events
- `apps/hello.py` — minimal “Hello”
- Upstream guide: [appguide](https://wasp-os.readthedocs.io/en/latest/appguide.html)

### App contract (duck typing)

No required base class. The system looks for members by name:

| Member | Required | Purpose |
|--------|----------|---------|
| `NAME` | yes | Launcher label (keep short, ~8 chars if possible) |
| `ICON` | recommended | Launcher icon (RLE, ≤ ~96×64) |
| `foreground()` | yes | App becomes active; full redraw |
| `background()` | optional | Cleanup when leaving |
| `sleep()` / `wake()` | optional | Stay registered across sleep |
| `preview()` | watch faces | Face picker preview |
| `touch` / `swipe` / `press` / tick handlers | optional | Input and timers |

### Minimal example

```python
# apps/hello_fork.py — example only; enable via wasp.toml if you want it frozen
import wasp

class HelloForkApp:
    NAME = "Hello"

    def foreground(self):
        self._draw()
        wasp.system.request_event(
            wasp.EventMask.TOUCH
            | wasp.EventMask.SWIPE_UPDOWN
            | wasp.EventMask.BUTTON
        )
        wasp.system.request_tick(1000)

    def tick(self, ticks):
        wasp.system.keep_awake()
        # optional periodic work

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill()
        draw.string("Hello, fork!", 0, 108, width=240)
```

Register:

```toml
[[app]]
file = 'apps/hello_fork.py'
```

Class name must end in `App` for the software installer / registry conventions used by wasp (e.g. `HelloForkApp`).

### Workflow (recommended)

1. **Edit on the host** under `apps/` or `watch_faces/`.
2. **Simulator first:** `./tools/run-sim-podman.sh` (see [tooling.md](tooling.md)).
3. Iterate until UI and memory feel right (heap is tight; avoid large allocations).
4. Add to `wasp.toml` when you want it in the frozen image.
5. **Build + OTA:** `./tools/build-flash-pinetime.sh all`.
6. Optional quick test without full rebuild: `./tools/wasptool --upload apps/my_thing.py` then load from the Software app / REPL (not frozen until rebuild).

**Important (simulator + `wasp.toml` apps):** `make sim` runs `configure_wasp_apps.py`, which **copies** listed apps into `wasp/apps/user/`. The simulator imports those copies (`apps.user.*`), not `apps/*.py` directly. After editing an enabled app, **restart the sim** (or re-copy into `wasp/apps/user/`) so you are not testing a stale file. Generated `wasp/apps/user/` is not committed.

### Useful APIs

- `wasp.system` — events, ticks, navigate, notifications, brightness
- `wasp.watch` — `drawable`, RTC, battery, sensors, vibrator
- `wasp.EventMask` / `wasp.EventType` — touch, swipe, button
- `widgets` — buttons, spinners, checkboxes, scrolls
- `draw565` — drawing helpers via `wasp.watch.drawable`

Only one app is **foreground** at a time. Backgrounded apps should keep enough state that reopening feels continuous.

### Memory and style

- Prefer small state, incremental redraws, and existing patterns from nearby apps.
- MicroPython: no full CPython stdlib; keep dependencies minimal.
- PEP 8 style; respect SPDX/copyright headers on files you copy.
- Do not commit generated trees (`build-*`, processed `watch.py`, accidental `*.mpy` unless intentional).

### Log of apps you add

Use this section as a scratch pad when you write new fork-only apps:

| Date | File | NAME | Status | Notes |
|------|------|------|--------|-------|
| 2026-08-13 | `apps/memory.py` | Memory | in wasp.toml (Software enable) | Also fine to `--exec` while iterating |
| *(next)* | `apps/…` | … | sim / on-device | … |

---

## Related

- [README.md](README.md) — fork overview
- [tooling.md](tooling.md) — sim, build, DFU
- [`AGENTS.md`](../../AGENTS.md) — full agent/project constitution
- Upstream: `docs/appguide.rst`, `apps/template.py`
