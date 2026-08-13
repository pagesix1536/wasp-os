# Apps on this fork

Notes for optional apps and watch faces shipped in **this** PineTime build. Upstream still has the full app guide in Sphinx (`docs/appguide.rst`); use this file as the fork’s living list and a short starter for new work.

App selection is controlled by root [`wasp.toml`](../../wasp.toml). Nothing under `apps/` is frozen into firmware until it is listed there and you rebuild / OTA.

---

## Currently enabled (`wasp.toml`)

### Quick ring (swipe left/right from the clock)

| File | Launcher name | Notes |
|------|---------------|--------|
| `apps/stopwatch.py` | Stopwatch | Quick-ring |
| `apps/heart.py` | Heart | Quick-ring; HRS3300 on device |

### Auto-loaded (available without freesteading)

| File | Notes |
|------|--------|
| `apps/alarm.py` | Alarms; may write `alarms.txt` on device (gitignored locally if present) |
| `apps/timer.py` | Countdown timer |
| `apps/faces.py` | Watch-face picker (`no_except = true`) |

### Launcher apps (this build)

| File | Launcher name | Notes |
|------|---------------|--------|
| `apps/calculator.py` | Calculator | |
| `apps/disa_b_l_e.py` | (BLE helper) | Disable/enable BLE from the watch |
| `apps/flashlight.py` | Torch | Bright / red screen flashlight |
| `apps/music_player.py` | Music | Gadgetbridge music control |
| `apps/phone_finder.py` | Find phone | Gadgetbridge “find phone” |
| `apps/weather.py` | Weather | Gadgetbridge weather units (this tree: weather only) |

### Watch faces

| File | Default? |
|------|----------|
| `watch_faces/clock.py` | No — digital clock (currently 24h-oriented) |
| `watch_faces/week_clock.py` | **Yes** (`default = true`) |
| `watch_faces/chrono.py` | No |

Gadgetbridge-related apps (music, phone finder, weather) need a phone companion that speaks the Gadgetbridge protocol. They still appear in the launcher without a phone; live data requires the link.

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
| *(example)* | `apps/…` | … | sim / on-device | … |

---

## Related

- [README.md](README.md) — fork overview
- [tooling.md](tooling.md) — sim, build, DFU
- [`AGENTS.md`](../../AGENTS.md) — full agent/project constitution
- Upstream: `docs/appguide.rst`, `apps/template.py`
