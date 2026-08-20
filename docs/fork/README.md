# This fork (pagesix1536/wasp-os)

Personal development fork of [wasp-os](https://github.com/wasp-os/wasp-os) for a **Pine64 PineTime**. Upstream is effectively dormant for new contributions; this fork is **not** aimed at merge requests or the official Sphinx/Read the Docs site.

Day-to-day notes for humans and AI agents live here under `docs/fork/` (Markdown). Agent project constitution stays at the repo root in [`AGENTS.md`](../../AGENTS.md).

## Remotes

| Remote | URL | Role |
|--------|-----|------|
| `origin` | `git@github.com:pagesix1536/wasp-os.git` | This fork — push here |
| `upstream` | `https://github.com/wasp-os/wasp-os.git` | Official wasp-os — fetch / merge only |

```sh
git push                     # → origin (GitHub)
git fetch upstream
git merge upstream/master    # optional: pull official updates
```

## What this fork adds

Fork-specific material (not expected upstream):

| Path | Purpose |
|------|---------|
| [`AGENTS.md`](../../AGENTS.md) | Project constitution for agents and humans |
| [`docs/fork/`](.) | Markdown docs for this fork (you are here) |
| [`tools/run-sim-podman.sh`](../../tools/run-sim-podman.sh) | Simulator in the project Podman image (Fedora/X11) |
| [`tools/build-flash-pinetime.sh`](../../tools/build-flash-pinetime.sh) | Build `micropython.zip` + OTA flash helper |
| [`tools/bleak_legacy_dfu.py`](../../tools/bleak_legacy_dfu.py) | Nordic legacy DFU over bleak (modern BlueZ) |
| [`wasp.toml`](../../wasp.toml) | Custom app / watch-face set for this PineTime |

Stock tree docs remain in reStructuredText under `docs/*.rst` and power the upstream Read the Docs site. Prefer **this directory** for anything specific to the fork, Fedora/Podman workflow, or personal app notes.

## Hardware target

| Item | Value |
|------|--------|
| Device | Pine64 PineTime |
| Make board | `BOARD=pinetime` |
| MCU | nRF52832 + SoftDevice S132 |
| Display | 240×240 RGB565 (ST7789) |
| OS language | MicroPython (constrained RAM/flash) |

## Development model (short)

| Activity | Where |
|----------|--------|
| Edit apps, git, docs | Host (e.g. Fedora) |
| `make sim`, `make check`, firmware builds | Project Ubuntu container (Podman) only |
| OTA / REPL / wasptool | Host Bluetooth |

Do **not** use a generic Grok/dev container for wasp builds. Use the image from `tools/docker/` (`make build-docker-image`).

Details:

- [CHANGES.md](CHANGES.md) — **concise log** of fork fixes, updates, features, and tooling
- [tooling.md](tooling.md) — helper scripts, Podman, DFU, wasptool, sim battery screenshots
- [apps.md](apps.md) — enabled apps, how to add new ones
- [operations.md](operations.md) — **ops playbook**: `--exec`, OTA, boot/heap gotchas, BLE debug, status-bar battery meter (also summarized in `AGENTS.md`)
- [raise-to-wake.md](raise-to-wake.md) — raise-to-wake research (deferred); pitfalls if revived (issue #6)

## Quick start

```sh
# Once: toolchain image + SoftDevice/submodules (see tooling.md)
make build-docker-image

# Simulator (SDL window on host display)
./tools/run-sim-podman.sh

# Build firmware from wasp.toml, then OTA to PineDFU
./tools/build-flash-pinetime.sh all
```

## Intentional non-goals

- No PRs/MRs to upstream wasp-os unless that changes later.
- No Sphinx integration for fork Markdown (these files are read as GitHub-rendered Markdown only).
- Upstream `README.rst` and `docs/*.rst` stay largely stock so merges from `upstream` stay simple.

## Related upstream docs

Useful when writing apps or understanding the OS (not fork-specific):

- [App guide](https://wasp-os.readthedocs.io/en/latest/appguide.html) (`docs/appguide.rst`)
- [Install guide](https://wasp-os.readthedocs.io/en/latest/install.html) (`docs/install.rst`)
- [API / reference](https://wasp-os.readthedocs.io/en/latest/wasp.html) (`docs/wasp.rst`)
