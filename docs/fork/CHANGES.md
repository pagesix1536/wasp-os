# Fork changes (pagesix1536/wasp-os)

Concise log of work on this personal PineTime fork since it diverged from upstream wasp-os. Not a full git history — short bullets only. Issue numbers refer to this fork’s GitHub issues.

## Bugs fixed

- **Battery meter fill (issue #3)** — 100% now fills body + nub as one continuous bar; 1px outer inset; red at ≤15%; charging still shows the bolt.
- **Battery % docs** — `drivers/battery.py` comments match the real curve (4.2 V → 100%, 3.5 V → 0%).

## Updates to existing apps / UI

- **Alarm (issue #12)** — rebuilt edit (weekday/weekend columns, SAV/DEL, 1-minute steps) and ringing (swipe stop/snooze, dead side button, 2-minute auto-stop).
- **Settings (issue #13)** — four dual-panel pages (Levels / Sleep / Time / Date); US MM-DD-YY on Date; widgets built in `foreground()`, dropped in `background()` to save heap.
- **Settings Timeout (issue #5)** — adjustable blank timeout (5–60 s) via `blank_after`.
- **Timer (issue #2)** — spinners only while foregrounded; removed from quick ring (still frozen / Software-enable).
- **Boot app set (issue #2)** — Heart / Weather / Music no longer `auto_load` (frozen for Software); leaner heap at boot.
- **Default watch face (issue #1)** — sole face is US 12-hour `clock_us` (am/pm + US date); stock `clock` / `week_clock` not in `wasp.toml`.

## New features / apps

- **Gadgetbridge battery** — on battery-glyph redraw, watch pushes `t:"status"` (`bat` / `volt` / `chg`) when BLE UART is connected.
- **Memory app** — heap readout utility (focus on **GC**); enable via Software.
- **Storage app** — frozen for Software enable (with the leaner boot set).

## Tooling & infrastructure

- Fedora **Podman** sim / build helpers (`run-sim-podman.sh`, `build-flash-pinetime.sh`).
- **bleak** legacy DFU client for modern BlueZ (replaces flaky gatttool path).
- GitHub `origin` (`pagesix1536/wasp-os`); dropped personal Gitea remote docs.
- Disabled fork CI: binary-dist workflow (`main.yml`) and simulator tests (`sim.yml`) — local Podman covers builds/tests.
- `.gitignore` for sim runtime files (`Morse.txt`, `alarms.txt`) and pynus submodule noise.
- Battery meter sim screenshot helper → `/tmp/wasp-battery-meter/` (keeps `res/` clean).

## Documentation

- `AGENTS.md` — project constitution for agents/humans.
- `docs/fork/` — README, tooling, apps, operations playbook.
- Raise-to-wake research notes (issue #6) — **not shipped**; button (+ charge) wake only.

## Deferred / research (not in firmware)

- **Raise-to-wake / tap-to-wake (issue #6)** — investigated; simple accel pose gate deferred after soak testing (false wakes vs misses). See [raise-to-wake.md](raise-to-wake.md).
