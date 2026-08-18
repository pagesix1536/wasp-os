# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2026 Chris Miller
"""SPI NOR flash storage utilization (issue #8)."""

import os
import wasp


class StorageApp():
    """Display SPI NOR (/flash) storage utilization."""
    NAME = 'Storage'

    def foreground(self):
        self._draw()

    def _draw(self):
        draw = wasp.watch.drawable
        draw.fill()
        draw.string('Storage', 0, 6, width=240)

        draw.string('SPI NOR', 12, 48)
        try:
            s = os.statvfs('/flash')
            bs = s[0]
            if not bs:
                raise OSError
            total = s[2] * bs
            free = s[3] * bs
            used = total - free
            # MB with one decimal, integer math only
            t10 = (total * 10 + 524288) // 1048576
            f10 = (free * 10 + 524288) // 1048576
            pct = (used * 100) // total if total else 0
            draw.string('Total: {}.{} MB'.format(t10 // 10, t10 % 10), 12, 84)
            draw.string('Free:  {}.{} MB'.format(f10 // 10, f10 % 10), 12, 120)
            draw.string('Used:  {}%'.format(pct), 12, 156)
        except (AttributeError, OSError):
            draw.string('Not supported', 12, 84)
