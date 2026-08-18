# Operational playbook (PineTime + this fork)

How we actually develop, flash, and debug the watch. Complements [tooling.md](tooling.md) and [apps.md](apps.md). A shorter copy lives in root [`AGENTS.md`](../../AGENTS.md) so agents always see it.

## Memory reality (nRF52832)

- Chip: **64 KB RAM** total — not all available to Python.
- After SoftDevice + MicroPython + display/drivers + a few registered apps, **free heap is often ~8–12 KB**.
- **Frozen** code lives in flash (cheap). **Registered instances**, widget trees, and **on-device compile** (`--exec` / freestead import) eat heap.
- `apps/memory.py` Boot / Init / Now / GC = `gc.mem_free()` snapshots at board bring-up, after `register_defaults`, at open, and after `gc.collect()`.

## Prefer `--exec` for live app testing

Docs path (`docs/appguide.rst`): paste into REPL and register — **not** SPI freestead via Software.

```sh
cd ~/git/wasp-os   # or your clone path

# One PineTime on, others off → omit --device
./tools/wasptool \
  --exec apps/myapp.py \
  --eval "wasp.system.register(MyApp())"
```

- Class name in `--eval` must match the file (`MemoryApp`, …).
- App appears in the **launcher** until **reboot** (or long-press OTA then back).
- Re-run after each edit. If sticky/weird, reboot then `--exec` again.
- **`MemoryError` during paste:** heap too tight — reboot, disable auto-load apps in Software, drop launcher instances via REPL, or freeze instead.

Do **not** rely on uploading to SPI `apps/foo.py` + Software checkbox for freesteading on current master: frozen package `apps` only exposes `system` and `user`, so `import apps.foo` fails even if the file exists.

## Ship lasting apps: freeze + OTA

1. Edit `wasp.toml` (`[[app]]` / `[[watchface]]`, `quick_ring`, `auto_load`, `default`).
2. `./tools/build-flash-pinetime.sh build`
3. Watch awake → `./tools/wasptool --bootloader` (or hold side button ~5s for PineDFU).
4. `./tools/build-flash-pinetime.sh flash`

Helpers: SoftDevice 403 → copy from bootloader tree; DFU via `tools/bleak_legacy_dfu.py` + `.venv-dfu`. Details in [tooling.md](tooling.md).

### `wasp.toml` flags

| Flag | Meaning |
|------|---------|
| `quick_ring = true` | Register at boot; swipe L/R from clock |
| `auto_load = true` | Register at boot; launcher (swipe up) |
| Neither | Frozen only; enable in **Software** when wanted |
| Watch face `default = true` | Boot face (exactly one) |

**Always registered by core (not toml):** Step counter (quick ring), Settings, Software (launcher).

## Critical boot gotchas

### Stuck screen showing only `main.py`

Last boot banner before UI. Usually:

1. **Missing dependency** — e.g. `week_clock` without `clock` in `wasp.toml` → `ImportError: apps.user.clock` → `schedule()` dies.  
2. **OOM / half `register_defaults()`** — too many `auto_load` apps; Settings/Software/Steps never finish; `_scheduling` stays false; little or no touch/button.

**Recover:** long-press reboot; if repeatable, lean `auto_load` and OTA. Agent can BLE Ctrl-C, inspect `quick_ring` / `launcher_ring` / `mem_free` / `hasattr(system,'sleep_at')`.

### `WeekClock` needs `Clock` (if re-enabled)

This fork’s default face is sole `clock_us.py` (self-contained). If you re-add stock `WeekClockApp`, it subclasses `ClockApp` (`from apps.user.clock import …`) — freeze **both** `week_clock` and `clock` in `wasp.toml` or boot hangs on `main.py`.

### Inverted / washed-out display after a crash

**CrashApp** toggles ST7789 invert. Leaving crash recovery can leave white background / dark glyphs.  
Fix: reboot, or `wasp.watch.display.invert(True)` then redraw (panel “normal” uses that polarity in wasp’s CrashApp restore path).

### Half-init: `sleep_at` missing

`Manager.sleep_at` is set only in the first-path `secondary_init`. If boot aborts early then something sets `system.app` and enables scheduling, ticks can raise `AttributeError: sleep_at` → CrashApp. Set `wasp.system.sleep_at = wasp.watch.rtc.uptime + 90` when recovering, or reboot cleanly.

## Talking to the watch (BLE)

| Goal | Command |
|------|---------|
| Live test app | `wasptool --exec … --eval "wasp.system.register(…)"` |
| REPL | `wasptool --console` → after Ctrl-C, `wasp.system.run()` to resume UI |
| Heap | `wasptool --memfree` |
| Enter DFU | `wasptool --bootloader` or hold button ~5s |
| OTA zip | `./tools/build-flash-pinetime.sh flash` |

- Omit `--device` if only one NUS/MicroPython watch is on.  
- wasp advertises mainly **NUS** (few GATT services) vs InfiniTime’s many; Gadgetbridge icons stay thin.  
- Phone↔watch **commands** (music transport) often work; **metadata/weather push** is flaky — don’t depend on it.  
- Keep other house watches off during scans.

## Simulator notes

- `./tools/run-sim-podman.sh` (host X11). Prefer launching from a real terminal if agent-started SDL feels frozen.  
- `make sim` copies `wasp.toml` apps into `wasp/apps/user/` — edit `apps/*.py` then **restart sim** or re-copy.  
- Free RAM / SPI flash stats often **“Not supported”** / n/a in sim.

## Tracking work

- **GitHub Issues** on this fork = idea/bug backlog (e.g. [#1 US watch face](https://github.com/pagesix1536/wasp-os/issues/1)).  
- Prefer labels like `enhancement`, `bug`, `heap`, `watchface`.  
- Skip Projects/Milestones unless the owner asks.
