#!/usr/bin/env python3
"""Capture Settings dual-panel pages in the simulator (agent verification)."""
import os
import sys

# Ensure system apps import path matches make sim
sys.path[:0] = ['.', 'wasp/boards/simulator', 'wasp', 'wasp/apps/system']

import wasp
import display
import settings

OUT = 'res/settings-layout-study'
os.makedirs(OUT, exist_ok=True)

wasp.system.secondary_init()
app = settings.SettingsApp()
wasp.system.switch(app)

names = ['levels', 'sleep', 'time', 'date']
for i, name in enumerate(names):
    app._sett_index = i
    app._draw()
    display.window.refresh()
    path = '{}/sim-page-{}-{}.png'.format(OUT, i + 1, name)
    display.save_image(display.windowsurface, path)
    print('wrote', path)

print('done')
