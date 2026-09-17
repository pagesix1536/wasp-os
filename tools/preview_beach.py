#!/usr/bin/env python3
"""Draw BeachApp in the SDL simulator and save a preview PNG."""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path[:0] = [ROOT, os.path.join(ROOT, 'wasp/boards/simulator'),
                os.path.join(ROOT, 'wasp')]

os.makedirs('gallery', exist_ok=True)
if os.path.isfile('res/beach.bmp'):
    shutil.copy('res/beach.bmp', 'gallery/beach')

import wasp
from display import save_image, windowsurface
from watch_faces.beach import BeachApp

wasp.system.secondary_init()
app = BeachApp()
wasp.system.switch(app)
app.preview()

out = 'res/screenshots/BeachApp.png'
os.makedirs(os.path.dirname(out), exist_ok=True)
save_image(windowsurface, out)
print('Saved:', out)
