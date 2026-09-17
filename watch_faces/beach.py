# Prototype analogue face over gallery/beach (issue #19 exploration).

"""Beach analogue prototype
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Streams ``gallery/beach`` (RGB565 BMP) line-by-line, then draws hour
and minute hands matching Chrono geometry in black. On a minute
change, re-blits a padded row band covering the old hands before
drawing the new ones. No ticks, no centre hub.
"""

import math
import wasp

_CX = 120
_CY = 120
_R0 = 5
_HOUR_R = 75
_MIN_R = 106
_HOUR_W = 7
_MIN_W = 5
_PAD = 4
_PATH = 'gallery/beach'
_BLACK = 0


class BeachApp():
    """Analogue hands on a streamed beach bitmap."""
    NAME = 'Beach'

    def __init__(self):
        self._hh = -1
        self._mm = -1

    def foreground(self):
        wasp.system.bar.clock = False
        # switch() mutes the panel around foreground(); turn it back on
        # so the BMP stream is visible line-by-line.
        wasp.watch.display.mute(False)
        self._draw(True)
        wasp.system.request_tick(1000)

    def sleep(self):
        return True

    def wake(self):
        self._draw()

    def tick(self, ticks):
        self._draw()

    def preview(self):
        wasp.system.bar.clock = False
        wasp.watch.display.mute(False)
        self._draw(True)

    def _angles(self, hh, mm):
        hour = (30 * (hh % 12)) + (mm / 2)
        minute = 6 * mm
        return hour, minute

    def _span(self, theta, r1, width):
        rad = theta * math.pi / 180
        s = math.sin(rad)
        c = math.cos(rad)
        y0 = _CY - int(c * _R0)
        y1 = _CY - int(c * r1)
        extra = (width // 2) + _PAD
        ymin = min(y0, y1) - extra
        ymax = max(y0, y1) + extra
        if ymin < 0:
            ymin = 0
        if ymax > 239:
            ymax = 239
        return ymin, ymax

    def _old_band(self):
        hour, minute = self._angles(self._hh, self._mm)
        a0, a1 = self._span(hour, _HOUR_R, _HOUR_W)
        b0, b1 = self._span(minute, _MIN_R, _MIN_W)
        y0 = a0 if a0 < b0 else b0
        y1 = a1 if a1 > b1 else b1
        return y0, y1

    def _blit(self, y0, y1):
        display = wasp.watch.display
        try:
            f = open(_PATH, 'rb')
        except OSError:
            wasp.watch.drawable.fill(_BLACK, 0, y0, 240, y1 - y0 + 1)
            return

        try:
            if f.read(2) != b'BM':
                return
            f.seek(0x0A)
            data_offset = int.from_bytes(f.read(4), 'little')
            f.seek(0x0E)
            if int.from_bytes(f.read(4), 'little') != 124:
                return
            width = int.from_bytes(f.read(4), 'little')
            height = int.from_bytes(f.read(4), 'little')
            if height >= 2147483648:
                height = 4294967296 - height
                bottom_up = False
            else:
                bottom_up = True
            if width > 240 or height > 240:
                return
            f.seek(0x1C)
            if int.from_bytes(f.read(2), 'little') != 16:
                return
            if int.from_bytes(f.read(4), 'little') != 3:
                return
            f.seek(0x36)
            if f.read(4) != b'\x00\xF8\x00\x00':
                return
            if f.read(4) != b'\xE0\x07\x00\x00':
                return
            if f.read(4) != b'\x1F\x00\x00\x00':
                return

            xoff = (240 - width) // 2
            if y0 < 0:
                y0 = 0
            if y1 >= height:
                y1 = height - 1
            display.set_window(xoff, y0, width, y1 - y0 + 1)
            buf = display.linebuffer[:2 * width]
            for y in range(y0, y1 + 1):
                row = (height - 1 - y) if bottom_up else y
                f.seek(data_offset + row * width * 2)
                f.readinto(buf)
                for x in range(0, width):
                    buf[x * 2], buf[x * 2 + 1] = buf[x * 2 + 1], buf[x * 2]
                display.write_data(buf)
        finally:
            f.close()

    def _hands(self, hh, mm):
        draw = wasp.watch.drawable
        hour, minute = self._angles(hh, mm)
        draw.polar(_CX, _CY, hour, _R0, _HOUR_R, _HOUR_W, _BLACK)
        draw.polar(_CX, _CY, hour, _R0, 60, 3, _BLACK)
        draw.polar(_CX, _CY, minute, _R0, _MIN_R, _MIN_W, _BLACK)

    def _draw(self, redraw=False):
        now = wasp.watch.rtc.get_localtime()
        if not redraw:
            if self._mm == now[4] and self._hh == now[3]:
                return
            if self._hh >= 0:
                y0, y1 = self._old_band()
                self._blit(y0, y1)

        if redraw:
            wasp.watch.drawable.fill()
            self._blit(0, 239)

        self._hh = now[3]
        self._mm = now[4]
        self._hands(self._hh, self._mm)
