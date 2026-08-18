#!/usr/bin/env python3
"""Draw ClockUsApp in the SDL simulator and save a preview PNG.

Run inside the project container (or any env with sim deps), e.g.:
  ./tools/run-sim-podman.sh  # interactive
  # or non-interactive:
  podman run ... wasp-os/wasp-os-dev:0.1.0 \\
    bash -lc 'cd /project && PYTHONPATH=.:wasp/boards/simulator:wasp \\
      python3 tools/preview_clock_us.py'
"""
import os
import sys

# Match `make sim` / `make check` path setup
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path[:0] = [ROOT, os.path.join(ROOT, 'wasp/boards/simulator'),
                os.path.join(ROOT, 'wasp')]

import wasp
from display import save_image, windowsurface
from apps.user.clock_us import ClockUsApp

# Sanity-check 12h conversion without needing the display.
cases = [
    (0, 12, 'am'),
    (1, 1, 'am'),
    (11, 11, 'am'),
    (12, 12, 'pm'),
    (13, 1, 'pm'),
    (23, 11, 'pm'),
]
app = ClockUsApp()
for hour24, expect_h, expect_ampm in cases:
    h, ampm = app._hour12(hour24)
    assert (h, ampm) == (expect_h, expect_ampm), (hour24, h, ampm)

wasp.system.secondary_init()
wasp.system.switch(app)
# Force a full redraw
app.preview()

out = 'res/screenshots/ClockUsApp.png'
os.makedirs(os.path.dirname(out), exist_ok=True)
save_image(windowsurface, out)
print('Saved:', out)
print('Date sample:', app._day_string(wasp.watch.rtc.get_localtime()))
print('OK')
