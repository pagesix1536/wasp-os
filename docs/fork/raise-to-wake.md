# Raise-to-wake (PineTime / this fork)

Fork research tracked as [GitHub issue #6](https://github.com/pagesix1536/wasp-os/issues/6).  
Originally proposed as **tap-to-wake**; explored as **raise-to-wake** after hardware investigation.

## Status: deferred (firmware reverted)

**2026-08-19:** Raise-to-wake was prototyped on-device, then **removed from the running firmware**. Wake is back to **stock wasp**: side button (and charging change). This document is kept so the fork (and anyone else) does not re-learn the same dead ends.

**Why stop:** A simple any-motion tip + static pose gate is inherently ambiguous (walking, pot-lifts, hands-at-sides vs a real glance). Dialing it “less sensitive” trades false wakes for missed raises. Trustworthy raise-to-wake needs InfiniTime-class history / roll detection (and power/heap budget wasp does not comfortably spare). Not worth endless threshold OTAs on this project right now.

To revive later: re-apply the approach below (or a fuller software detector), starting from the pitfalls section.

## Why not tap-to-wake?

| Layer | Stock wasp sleep | Implication |
|-------|------------------|-------------|
| CST816S | `watch.touch.sleep()` → deep sleep cmd `0xA5=0x03` (or hold reset) | **No touch IRQs** while blanked |
| Asleep `_tick` | Only button + charging change wake | Touch events ignored even if present |
| CST816S monitor mode | ~100 µA vs ~5 µA deep sleep | Tap-wake is possible if touch is left out of deep sleep (InfiniTime does this for double-tap) |

InfiniTime proves tap/double-tap wake on the same chip by **not** deep-sleeping touch when those modes are on. On wasp, battery is already tighter than InfiniTime, so this fork preferred accel-based wake.

Bosch **`WRIST_WEAR`** hardware gesture was tried on PineTime and **never asserted** reliably (even with APS off, INT mapped, axis remap). InfiniTime also uses a **software** raise detector rather than `WRIST_WEAR`.

## What was prototyped (then reverted from firmware)

```
any-motion IRQ (BMA INT1 → ACCEL_INT / P0.08)
        ↓
  Python flag + schedule tick
        ↓
  viewing-pose check (accel_xyz, orientation-corrected)
        ↓
  Manager.wake()
```

### Configuration used in the prototype (`BMA421.reset()` when enabled)

| Item | Value | Notes |
|------|--------|------|
| Advance power-save | **off** (`POWER_CONF` bit 0 clear) | Feature IRQs do not fire with APS on |
| Any-motion threshold | `120` (~0.48 mg/LSB) | Was far lower; typing woke the watch |
| Any-motion duration | `8` (~20 ms/LSB) | Require sustained slope |
| Axes | **X \| Y** only | Skip Z to reduce table taps |
| INT1 IO (`0x53`) | **`0x08`** | Output enable, **active-low**. **Never `0x0A`** (active-high → pin stuck low → sleep/wake loop if level-polled) |
| Interrupt map | `ANY_MOT_INT` on `INTR1_MAP` | Not `WRIST_WEAR_INT` |

### Viewing pose (`_is_viewing_pose`)

Orientation-corrected LSB (~1024 ≈ 1g at ±2g):

- Reject if `|Z| > 500` (too flat).
- Require `|Y| ≥ 700` and `|Y| ≥ |Z| + 200` (upright-ish).
- Reject if `|X| > 450` (rolled; button not “left”).

After motion IRQ, pose is checked immediately; if not yet upright, wait **120 ms** and check again (raise often trips mid-gesture).

### System integration

| File | Role |
|------|------|
| `wasp/drivers/bma421.py` | IRQ, any-motion setup, pose gate, `get_wake_event` / `clear_wake` |
| `wasp/boards/pinetime/watch.py.in` (and p8) | `BMA421(..., intr=Pin('ACCEL_INT'), schedule=_callback)` |
| `wasp/wasp.py` | Drain/check `get_wake_event` every tick; wake when asleep; `clear_wake()` on `sleep()` |
| `wasp/modules/bma42x-upy/bma42x.c` | Exports `WRIST_WEAR_INT`, `set_remap_axes` (remap unused in final path) |

Simulator / sphinx stubs implement no-op `get_wake_event` / `clear_wake`.

## Hard-won pitfalls (do not regress)

1. **`0x53 = 0x0A` is wrong for active-low** — leaves `ACCEL_INT` idle **low**. Combined with “wake if pin==0” polling → **instant sleep/wake loop**.
2. **Do not level-poll `ACCEL_INT==0` for wake** — only the IRQ edge flag (plus pose). Pin can stick asserted.
3. **APS must be off** or any-motion / feature status never sets.
4. **`map_interrupt` alone does not enable the INT pin driver** — must set INT1 IO ctrl.
5. **Bosch `WRIST_WEAR` ≠ workable raise-to-wake on this mount** without a long InfiniTime-style software filter; prefer any-motion tip + pose.
6. **Touch stays deep-slept** in `Manager.sleep()` — do not assume screen taps while blanked.
7. **wasptool multiline `--eval` / large `--exec`** often hits `MemoryError` or paste corruption; use tiny scripts after reboot, or OTA freeze for driver changes.
8. **Pose sampling over BLE** is unreliable if the watch sits on the desk next to the laptop — wearer must move *this* watch; prompts in the agent terminal are easy to miss.

## Power notes

- Leaving CST816S in monitor mode for tap-wake: roughly **~+95 µA** vs deep sleep (datasheet order of magnitude).
- Raise-to-wake pays: accel already on for steps; **APS off** + any-motion feature engine adds idle cost (measure on soak — owner testing).
- Short blank timeout (5s) increases UI on/off cycles if false wakes happen; use Settings Timeout **15–30s** for fairer battery comparisons.

## Tuning knobs

Edit `wasp/drivers/bma421.py` then rebuild/OTA (`./tools/build-flash-pinetime.sh all`):

- `set_any_mot_config(threshold=…, duration=…)` — sensitivity of the motion tip.
- `_is_viewing_pose()` thresholds — upright vs flat / roll.
- Optional later: Settings toggle, persist, restore `blank_after` default to 15.

## Related

- Issue #5 — adjustable screen timeout in Settings.
- Issue #6 — this feature.
- InfiniTime `SystemTask` / `MotionController::ShouldRaiseWake` — software raise; double-tap keeps touch awake.
