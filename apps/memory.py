# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2026 Chris Miller

import gc
import wasp

class MemoryApp():
    """Display free heap memory."""
    NAME = 'Memory'

    def foreground(self):
        self._draw()

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill()
        draw.string('Memory', 0, 6, width=240)

        if wasp.watch.free:
            draw.string('Boot: {}'.format(wasp.watch.free), 12, 3*24)
            draw.string('Init: {}'.format(wasp.free), 12, 4*24)
            draw.string('Now: {}'.format(gc.mem_free()), 12, 5*24)
            gc.collect()
            draw.string('GC: {}'.format(gc.mem_free()), 12, 6*24)
        else:
            draw.string('Not supported', 12, 4*24)
