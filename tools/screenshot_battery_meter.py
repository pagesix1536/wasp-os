#!/usr/bin/env python3
"""Force simulator battery states and screenshot the status-bar meter.

Writes under /tmp/wasp-battery-meter/ so test shots do not land in res/
alongside real UI icons.
"""
import os

import wasp
import watch
import display

OUT_DIR = '/tmp/wasp-battery-meter'


def force_battery(level=None, charging=False):
    """Override simulator battery readouts (disables the bouncing voltage)."""
    if charging:
        watch.battery.charging = lambda: True
        watch.battery.level = lambda: 0
    else:
        watch.battery.charging = lambda: False
        watch.battery.level = lambda: int(level)


def shot(name, level=None, charging=False):
    path = os.path.join(OUT_DIR, name)
    force_battery(level=level, charging=charging)
    # Force a full meter redraw after changing the mocked level.
    wasp.system.bar._meter.level = -2
    wasp.system.bar.draw()
    display.window.refresh()
    display.save_image(display.windowsurface, path)
    print('wrote', path, 'level=', level, 'charging=', charging)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    wasp.system.secondary_init()
    # Clock face always draws the status bar.
    wasp.system.switch(wasp.system.quick_ring[0])
    display.window.refresh()

    shot('battery-meter-100.png', level=100)
    shot('battery-meter-85.png', level=85)   # body full, nub empty
    shot('battery-meter-90.png', level=90)   # first nub pixel
    shot('battery-meter-50.png', level=50)
    shot('battery-meter-16.png', level=16)   # just above low threshold
    shot('battery-meter-15.png', level=15)   # critical red threshold
    shot('battery-meter-05.png', level=5)
    shot('battery-meter-00.png', level=0)
    shot('battery-meter-charging.png', charging=True)


if __name__ == '__main__':
    main()
