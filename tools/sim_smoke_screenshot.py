#!/usr/bin/env python3
"""One-shot simulator smoke: init UI, save a PNG, exit (do not run the loop)."""
import wasp
import display

wasp.system.secondary_init()
display.window.refresh()
out = "res/omarchy-sim-smoke.png"
display.save_image(display.windowsurface, out)
print("saved", out)
