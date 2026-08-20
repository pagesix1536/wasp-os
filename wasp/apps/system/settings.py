# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020-21 Daniel Thompson
# Copyright (C) 2026 Chris Miller

"""Settings application
~~~~~~~~~~~~~~~~~~~~~~~

Allows a very small set of user preferences (including the date and
time) to be set on the device itself.

Pages (swipe up/down):

1. **Levels** — Brightness + Notification Level
2. **Sleep** — Timeout (screen blank delay) + Units
3. **Time**
4. **Date**

Timeout writes ``wasp.system.blank_after`` immediately (choices
5 / 10 / 15 / 30 / 60 seconds; default 15). Like Brightness, it is not
persisted across reboot.

Widgets are built in :py:meth:`foreground` and released in
:py:meth:`background` so the always-registered Settings instance does
not keep a full control tree on the heap while unused (see issue #13 /
#2).

.. figure:: res/screenshots/SettingsApp.png
    :width: 179

.. note::

    The settings tool is not expected to comprehensively present every
    user configurable preference. Some are better presented via a
    companion app and some particular exotic ones are perhaps best
    managed with a user-provided ``main.py``.
"""


import wasp
import fonts
import icons
from micropython import const

# Dual-panel layout (240px tall). Slider.touch() is X-only, so Settings
# gates each slider by these Y bands.
_TOP_Y0 = const(0)
_TOP_Y1 = const(100)
_BOT_Y0 = const(100)
_BOT_Y1 = const(220)

# Bottom-panel geometry (Notification Level / Units) — kept clear of the
# divider at y=98 and the scroll arrows near the bottom.
_BOT_TITLE_Y = const(118)
_BOT_SLIDER_Y = const(145)
_BOT_SLIDER_LABEL_Y = const(186)
_BOT_BUTTON_Y = const(150)
_BOT_UNITS_LABEL_Y = const(198)

_TIMEOUT_OPTS = (5, 10, 15, 30, 60)
_UNITS = ('Metric', 'Imperial')
_PAGES = ('Levels', 'Sleep', 'Time', 'Date')

class SettingsApp():
    """Settings application."""
    NAME = 'Settings'
    ICON = icons.settings

    def __init__(self):
        # Keep only cheap page state at boot. Widgets are constructed in
        # foreground() and dropped in background().
        self._settings = _PAGES
        self._sett_index = 0
        self._current_setting = _PAGES[0]

    def _build_widgets(self):
        """Allocate UI controls used while Settings is in the foreground."""
        self._slider = wasp.widgets.Slider(3, 10, 28)
        self._nfy_slider = wasp.widgets.Slider(3, 10, _BOT_SLIDER_Y)
        self._timeout_slider = wasp.widgets.Slider(len(_TIMEOUT_OPTS), 10, 28)
        self._scroll_indicator = wasp.widgets.ScrollIndicator()
        self._HH = wasp.widgets.Spinner(50, 60, 0, 23, 2)
        self._MM = wasp.widgets.Spinner(130, 60, 0, 59, 2)
        # Date spinners in US order MM-DD-YY with 20px gaps for '-' separators
        self._mm = wasp.widgets.Spinner(10, 60, 1, 12, 1)
        self._dd = wasp.widgets.Spinner(90, 60, 1, 31, 1)
        self._yy = wasp.widgets.Spinner(170, 60, 20, 60, 2)
        self._units_toggle = wasp.widgets.Button(32, _BOT_BUTTON_Y, 176, 40, "Change")

    def _drop_widgets(self):
        """Release UI controls so they can be garbage-collected."""
        self._slider = None
        del self._slider
        self._nfy_slider = None
        del self._nfy_slider
        self._timeout_slider = None
        del self._timeout_slider
        self._scroll_indicator = None
        del self._scroll_indicator
        self._HH = None
        del self._HH
        self._MM = None
        del self._MM
        self._mm = None
        del self._mm
        self._dd = None
        del self._dd
        self._yy = None
        del self._yy
        self._units_toggle = None
        del self._units_toggle

    def _timeout_index(self):
        """Map current blank_after to the nearest slider step."""
        opts = _TIMEOUT_OPTS
        v = wasp.system.blank_after
        best = 0
        for i, o in enumerate(opts):
            if abs(o - v) < abs(opts[best] - v):
                best = i
        return best

    def _level_label(self, value, silent=False):
        if value == 3:
            return "High"
        if value == 2:
            return "Mid"
        return "Silent" if silent else "Low"

    def foreground(self):
        self._build_widgets()
        self._slider.value = wasp.system.brightness - 1
        self._draw()
        wasp.system.request_event(wasp.EventMask.TOUCH)
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)

    def background(self):
        self._drop_widgets()

    def touch(self, event):
        y = event[2]
        if self._current_setting == 'Levels':
            if _TOP_Y0 <= y < _TOP_Y1:
                self._slider.touch(event)
                wasp.system.brightness = self._slider.value + 1
            elif _BOT_Y0 <= y < _BOT_Y1:
                self._nfy_slider.touch(event)
                wasp.system.notify_level = self._nfy_slider.value + 1
        elif self._current_setting == 'Sleep':
            if _TOP_Y0 <= y < _TOP_Y1:
                self._timeout_slider.touch(event)
                wasp.system.blank_after = _TIMEOUT_OPTS[self._timeout_slider.value]
                # Apply immediately to the current wake period.
                wasp.system.keep_awake()
            elif self._units_toggle.touch(event):
                wasp.system.units = _UNITS[
                    (_UNITS.index(wasp.system.units) + 1) % len(_UNITS)
                ]
        elif self._current_setting == 'Time':
            if self._HH.touch(event) or self._MM.touch(event):
                now = list(wasp.watch.rtc.get_localtime())
                now[3] = self._HH.value
                now[4] = self._MM.value
                wasp.watch.rtc.set_localtime(now)
        elif self._current_setting == 'Date':
            if self._yy.touch(event) or self._mm.touch(event) \
                    or self._dd.touch(event):
                now = list(wasp.watch.rtc.get_localtime())
                now[0] = self._yy.value + 2000
                now[1] = self._mm.value
                now[2] = self._dd.value
                wasp.watch.rtc.set_localtime(now)
        self._update()

    def swipe(self, event):
        """Swipe up/down to move between the four settings pages."""
        if event[0] == wasp.EventType.UP:
            self._sett_index += 1
            self._draw()
        elif event[0] == wasp.EventType.DOWN:
            self._sett_index -= 1
            self._draw()

    def _draw_divider(self):
        draw = wasp.watch.drawable
        draw.fill(wasp.system.theme('mid'), 20, 98, 200, 1)

    def _draw(self):
        """Redraw the display from scratch."""
        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute
        self._current_setting = self._settings[self._sett_index % len(self._settings)]
        mute(True)
        draw.fill()
        draw.set_color(wasp.system.theme('bright'))

        if self._current_setting == 'Levels':
            draw.set_font(fonts.sans18)
            draw.string('Brightness', 0, 4, width=240)
            draw.string('Notification Level', 0, _BOT_TITLE_Y, width=240)
            self._draw_divider()
            self._slider.value = wasp.system.brightness - 1
            self._nfy_slider.value = wasp.system.notify_level - 1
        elif self._current_setting == 'Sleep':
            draw.set_font(fonts.sans18)
            draw.string('Timeout', 0, 4, width=240)
            draw.string('Units', 0, _BOT_TITLE_Y, width=240)
            self._draw_divider()
            self._timeout_slider.value = self._timeout_index()
            self._units_toggle.draw()
        elif self._current_setting == 'Time':
            draw.set_font(fonts.sans24)
            draw.string('Time', 0, 6, width=240)
            now = wasp.watch.rtc.get_localtime()
            self._HH.value = now[3]
            self._MM.value = now[4]
            draw.set_font(fonts.sans28)
            draw.string(':', 110, 120-14, width=20)
            self._HH.draw()
            self._MM.draw()
        elif self._current_setting == 'Date':
            draw.set_font(fonts.sans24)
            draw.string('Date', 0, 6, width=240)
            now = wasp.watch.rtc.get_localtime()
            self._yy.value = now[0] - 2000
            self._mm.value = now[1]
            self._dd.value = now[2]
            draw.set_font(fonts.sans28)
            # Hyphen separators in the 20px gaps (same idea as Time's ':')
            draw.string('-', 70, 120-14, width=20)
            draw.string('-', 150, 120-14, width=20)
            self._mm.draw()
            self._dd.draw()
            self._yy.draw()
            # One label per spinner column so each sits under its arrows
            draw.set_font(fonts.sans24)
            draw.string('MM', 10, 180, width=60)
            draw.string('DD', 90, 180, width=60)
            draw.string('YY', 170, 180, width=60)

        self._scroll_indicator.draw()
        self._update()
        mute(False)

    def _update(self):
        draw = wasp.watch.drawable
        draw.set_color(wasp.system.theme('bright'))
        if self._current_setting == 'Levels':
            self._slider.update()
            self._nfy_slider.update()
            draw.set_font(fonts.sans18)
            draw.string(self._level_label(wasp.system.brightness), 0, 68, width=240)
            draw.string(
                self._level_label(wasp.system.notify_level, silent=True),
                0, _BOT_SLIDER_LABEL_Y, width=240
            )
        elif self._current_setting == 'Sleep':
            self._timeout_slider.update()
            draw.set_font(fonts.sans18)
            secs = _TIMEOUT_OPTS[self._timeout_slider.value]
            draw.string('{} seconds'.format(secs), 0, 68, width=240)
            draw.string(wasp.system.units, 0, _BOT_UNITS_LABEL_Y, width=240)
