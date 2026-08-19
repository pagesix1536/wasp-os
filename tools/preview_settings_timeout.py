#!/usr/bin/env python3
"""Render Settings → Timeout page to res/SettingsTimeout.png (simulator)."""
import os
import sys

# Match make sim import path
sys.path[:0] = ['.', 'wasp/boards/simulator', 'wasp', 'wasp/apps/system']

import wasp
import display
from settings import SettingsApp

wasp.system.secondary_init()
# Use the stock default for a representative screenshot (sim main sets 300).
wasp.system.blank_after = 15

app = SettingsApp()
app._sett_index = app._settings.index('Timeout')
wasp.system.switch(app)
display.window.refresh()
os.makedirs('res', exist_ok=True)
out = 'res/SettingsTimeout.png'
display.save_image(display.windowsurface, out)
print('wrote', out, 'blank_after=', wasp.system.blank_after)
