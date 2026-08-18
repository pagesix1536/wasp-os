# Fork watch face (issue #1): US date + 12-hour clock with am/pm.
# Self-contained — does not subclass ClockApp / WeekClockApp.

"""US 12-hour digital clock
~~~~~~~~~~~~~~~~~~~~~~~~~~

Shows 12-hour time with a small am/pm marker, battery meter, and a
US-style date line (weekday, month, day — no year).
"""

import wasp

import fonts.clock as digits

DIGITS = (
        digits.clock_0, digits.clock_1, digits.clock_2, digits.clock_3,
        digits.clock_4, digits.clock_5, digits.clock_6, digits.clock_7,
        digits.clock_8, digits.clock_9
)

MONTH = 'JanFebMarAprMayJunJulAugSepOctNovDec'
WDAY = 'MonTueWedThuFriSatSun'

# Status bar occupies ~y0–32. Date sits under it; large digits and am/pm
# are shifted down vs stock (digit y=80) to make room.
_DATE_Y = 42
_DIGIT_Y = 96
_DIGIT_H = 60
_AMPM_Y = 164


class ClockUsApp():
    """Digital clock with 12-hour time and US date ordering."""
    NAME = 'Clock12h'

    def foreground(self):
        wasp.system.bar.clock = False
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
        self._draw(True)

    def _day_string(self, now):
        """US-style date without year, e.g. ``Wed, Aug 13``."""
        month = now[1] - 1
        month = MONTH[month*3:(month+1)*3]
        wday = now[6]
        wday = WDAY[wday*3:(wday+1)*3]
        return '{}, {} {}'.format(wday, month, now[2])

    def _hour12(self, hour24):
        """Convert 0–23 to (hour 1–12, 'am'|'pm')."""
        if hour24 >= 12:
            ampm = 'pm'
        else:
            ampm = 'am'
        hour = hour24 % 12
        if hour == 0:
            hour = 12
        return hour, ampm

    def _draw(self, redraw=False):
        draw = wasp.watch.drawable
        hi = wasp.system.theme('bright')
        lo = wasp.system.theme('mid')
        mid = draw.lighten(lo, 1)

        if redraw:
            now = wasp.watch.rtc.get_localtime()
            draw.fill()
            draw.blit(digits.clock_colon, 2*48, _DIGIT_Y, fg=mid)
            wasp.system.bar.draw()
        else:
            now = wasp.system.bar.update()
            if not now or self._min == now[4]:
                return

        hour, ampm = self._hour12(now[3])
        tens = hour // 10
        ones = hour % 10

        # Blank leading tens for 1–9 (clear so a prior "1" does not linger).
        if tens:
            draw.blit(DIGITS[tens], 0*48, _DIGIT_Y, fg=lo)
        else:
            draw.fill(0, 0*48, _DIGIT_Y, 48, _DIGIT_H)

        draw.blit(DIGITS[ones], 1*48, _DIGIT_Y, fg=hi)
        draw.blit(DIGITS[now[4] // 10], 3*48, _DIGIT_Y, fg=lo)
        draw.blit(DIGITS[now[4] % 10], 4*48, _DIGIT_Y, fg=hi)

        draw.set_color(mid)
        draw.string(ampm, 0, _AMPM_Y, width=240, right=True)

        draw.set_color(hi)
        draw.string(self._day_string(now), 0, _DATE_Y, width=240)

        self._min = now[4]
