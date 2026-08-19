# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
# Copyright (C) 2020 Joris Warmbier
# Copyright (C) 2021 Adam Blair
"""Alarm Application
~~~~~~~~~~~~~~~~~~~~

An application to set a vibration alarm. All settings can be accessed from the Watch UI.

List page: enable/disable via the checkbox; swipe left/right for the quick
ring. Edit page: SAV writes and returns to the list, DEL removes the slot,
the side button saves and goes to the clock, swipes are ignored. Ringing
page: swipe up to stop, swipe down to snooze 10 minutes; tap and the side
button do nothing. An unanswered alarm stops after two minutes.

    .. figure:: res/screenshots/AlarmApp.png
        :width: 179

        Screenshot of the Alarm Application

"""
import wasp
import fonts
import time
import widgets
import array
from micropython import const

# 2-bit RLE, generated from res/alarm_icon.png, 390 bytes
icon = (
    b'\x02'
    b'`@'
    b'\x17@\xd2G#G-K\x1fK)O\x1bO&O'
    b'\n\x80\xb4\x89\x0bN$N\x08\x91\tM"M\x07\x97'
    b'\x07M!L\x06\x9b\x07K K\x06\x9f\x06K\x1fJ'
    b'\x05\xa3\x05J\x1eJ\x05\x91\xc0\xd0\xc3\x91\x05J\x1dI'
    b'\x05\x8c\xcf\x8c\x05I\x1dH\x05\x8b\xd3\x8b\x05H\x1dG'
    b'\x05\x8a\xd7\x8a\x05G\x1dG\x04\x89\xdb\x89\x05F\x1dF'
    b'\x04\x89\xcc\x05\xcc\x89\x04F\x1dE\x04\x89\xcd\x05\xcd\x89'
    b'\x04E\x1eD\x03\x88\xce\x07\xce\x88\x04C\x1fC\x04\x88'
    b'\xce\x07\xce\x88\x04C\x1fC\x03\x88\xcf\x07\xcf\x88\x04A'
    b'!A\x04\x87\xd0\x07\xd0\x87\x04A%\x87\xd1\x07\xd1\x87'
    b")\x87\xd1\x07\xd1\x87(\x87\xd2\x07\xd2\x87'\x87\xd2\x07"
    b"\xd2\x87'\x86\xd3\x07\xd3\x86&\x87\xd3\x07\xd3\x87%\x86"
    b'\xd4\x07\xd4\x86%\x86\xd4\x07\xd4\x86%\x86\xd4\x07\xd4\x86'
    b'$\x87\xd4\x07\xd4\x87#\x87\xd4\x07\xd4\x87#\x87\xd4\x07'
    b'\xd4\x87#\x86\xd4\x08\xd5\x86#\x86\xd3\t\xd5\x86#\x86'
    b'\xd2\t\xd6\x86#\x87\xd0\n\xd5\x87#\x87\xcf\n\xd6\x87'
    b'#\x87\xce\n\xd7\x87$\x86\xce\t\xd8\x86%\x86\xce\x08'
    b'\xd9\x86%\x86\xcd\x08\xda\x86%\x87\xcc\x07\xda\x87%\x87'
    b"\xcc\x06\xdb\x86'\x87\xcc\x03\xdc\x87'\x87\xeb\x87(\x87"
    b'\xe9\x87)\x87\xe9\x87*\x87\xe7\x87+\x88\xe5\x88,\x87'
    b'\xe5\x87-\x88\xe3\x88.\x88\xe1\x880\x89\xdd\x892\x89'
    b'\xdb\x893\x8b\xd7\x8b2\x8d\xd4\x8e0\x91\xcf\x91.\x97'
    b'\xc5\x97,\xb5+\x88\x03\x9f\x03\x88*\x88\x05\x9d\x05\x88'
    b')\x87\t\x97\t\x87*\x85\x0c\x93\x0c\x85,\x83\x11\x8b'
    b'\x11\x83\x17'
)

# Enabled masks
_MONDAY = const(0x01)
_TUESDAY = const(0x02)
_WEDNESDAY = const(0x04)
_THURSDAY = const(0x08)
_FRIDAY = const(0x10)
_SATURDAY = const(0x20)
_SUNDAY = const(0x40)
_WEEKDAYS = const(0x1F)
_WEEKENDS = const(0x60)
_EVERY_DAY = const(0x7F)
_IS_ACTIVE = const(0x80)

# Alarm data indices
_HOUR_IDX = const(0)
_MIN_IDX = const(1)
_ENABLED_IDX = const(2)

# Pages
_HOME_PAGE = const(-1)
_RINGING_PAGE = const(-2)

# Colours (RGB565)
_WHITE = const(0xFFFF)
_RED = const(0xF800)
_YELLOW = const(0xFFE0)
_SAV_BG = const(0x07C0)
_DEL_BG = const(0xF800)

_RING_SECS = const(120)
_SNOOZE_MIN = const(10)

# Icon is 96x64. Time sits at the top; icon below it.
_ICON_X = const(72)
_ICON_Y = const(44)
_ICON_H = const(64)
_TIME_Y = const(4)
# STOP (sans24, 24 px) centered on the icon's vertical midpoint (y=76).
_STOP_Y = const(64)
# 4 px under STOP: up-arrow tip and down-arrow tail share this y.
_ARROW_ALIGN_Y = const(92)
# Down-arrow tip and up-arrow tail, just above SNOOZE.
_ARROW_POINT_Y = const(204)
_SNOOZE_Y = const(208)
_UP_ARROW_X = const(48)
_DOWN_ARROW_X = const(192)


class AlarmApp:
    """Allows the user to set a vibration alarm.
    """
    NAME = 'Alarm'
    ICON = icon

    def __init__(self):
        """Initialize the application."""

        self.page = _HOME_PAGE
        self.alarms = (bytearray(3), bytearray(3), bytearray(3), bytearray(3))
        self.pending_alarms = array.array('d', [0.0, 0.0, 0.0, 0.0])
        self._snooze_at = 0.0
        self._ring_started = 0
        self._ring_hh = 8
        self._ring_mm = 0

        self.num_alarms = 0
        try:
            with open("alarms.txt", "r") as f:
                alarms = f.readlines()[0].split(";")
            if "" in alarms:
                alarms.remove("")
            for alarm in alarms:
                n = self.num_alarms
                h, m, st = map(int, alarm.split(","))
                self.alarms[n][0] = h
                self.alarms[n][1] = m
                self.alarms[n][2] = st
                self.num_alarms += 1
        except Exception:
            pass
        self._set_pending_alarms()

    def foreground(self):
        """Activate the application."""

        self.save_btn = widgets.Button(136, 136, 100, 42, 'SAV')
        self.del_alarm_btn = widgets.Button(136, 190, 100, 42, 'DEL')
        self.hours_wid = widgets.Spinner(100, 0, 0, 23, 2)
        self.min_wid = widgets.Spinner(180, 0, 0, 59, 2, 1)
        self.day_btns = (widgets.ToggleButton(4, 4, 52, 44, 'Mo'),
                         widgets.ToggleButton(4, 52, 52, 44, 'Tu'),
                         widgets.ToggleButton(4, 100, 52, 44, 'We'),
                         widgets.ToggleButton(4, 148, 52, 44, 'Th'),
                         widgets.ToggleButton(4, 196, 52, 44, 'Fr'),
                         widgets.ToggleButton(62, 148, 52, 44, 'Sa'),
                         widgets.ToggleButton(62, 196, 52, 44, 'Su'))
        self.alarm_checks = (widgets.Checkbox(200, 57),
                             widgets.Checkbox(200, 102),
                             widgets.Checkbox(200, 147),
                             widgets.Checkbox(200, 192))

        self._deactivate_pending_alarms()
        if self.page == _RINGING_PAGE:
            self._write_alarms()
        self._draw()

        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_LEFTRIGHT |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.BUTTON)
        wasp.system.request_tick(1000)

    def background(self):
        """De-activate the application."""
        if self.page > _HOME_PAGE:
            self._save_alarm()

        self.page = _HOME_PAGE

        self.save_btn = None
        del self.save_btn
        self.del_alarm_btn = None
        del self.del_alarm_btn
        self.hours_wid = None
        del self.hours_wid
        self.min_wid = None
        del self.min_wid
        self.alarm_checks = None
        del self.alarm_checks
        self.day_btns = None
        del self.day_btns

        self._set_pending_alarms()
        self._write_alarms()

    def tick(self, ticks):
        """Notify the application that its periodic tick is due."""
        if self.page == _RINGING_PAGE:
            wasp.watch.vibrator.pulse(duty=50, ms=500)
            wasp.system.keep_awake()
            if wasp.watch.rtc.uptime - self._ring_started >= _RING_SECS:
                self._stop()
        elif self.page == _HOME_PAGE:
            wasp.system.bar.update()

    def press(self, button, state):
        """Notify the application of a button press event."""
        if not state:
            return
        if self.page == _RINGING_PAGE:
            return
        wasp.system.navigate(wasp.EventType.HOME)

    def swipe(self, event):
        """Notify the application of a swipe event."""
        if self.page == _RINGING_PAGE:
            if event[0] == wasp.EventType.UP:
                self._stop()
            elif event[0] == wasp.EventType.DOWN:
                self._snooze()
        elif self.page > _HOME_PAGE:
            return
        else:
            wasp.system.navigate(event[0])

    def touch(self, event):
        """Notify the application of a touchscreen touch event."""
        if self.page == _RINGING_PAGE:
            return
        if self.page > _HOME_PAGE:
            if self.hours_wid.touch(event) or self.min_wid.touch(event):
                return
            for day_btn in self.day_btns:
                if self._hit(day_btn, event):
                    day_btn.state = not day_btn.state
                    day_btn.draw()
                    return
            if self._hit(self.save_btn, event):
                self._save_alarm()
                self._write_alarms()
                self._draw()
                return
            if self._hit(self.del_alarm_btn, event):
                self._remove_alarm(self.page)
        elif self.page == _HOME_PAGE:
            for index, checkbox in enumerate(self.alarm_checks):
                if index < self.num_alarms and checkbox.touch(event):
                    if checkbox.state:
                        self.alarms[index][_ENABLED_IDX] |= _IS_ACTIVE
                    else:
                        self.alarms[index][_ENABLED_IDX] &= ~_IS_ACTIVE
                    self._write_alarms()
                    self._draw(index)
                    return
            for index, alarm in enumerate(self.alarms):
                # Open edit page for clicked alarms
                if index < self.num_alarms and event[1] < 190 \
                        and 60 + (index * 45) < event[2] < 60 + ((index + 1) * 45):
                    self.page = index
                    self._draw()
                    return
                # Add new alarm if plus clicked
                elif index == self.num_alarms and 60 + (index * 45) < event[2]:
                    self.num_alarms += 1
                    self._draw(index)
                    return

    def _hit(self, btn, event):
        """Exact widget box (no 10px inflate) so adjacent keys do not steal."""
        im = btn._im
        x = event[1]
        y = event[2]
        return (im[0] <= x < im[0] + im[2] and
                im[1] <= y < im[1] + im[3])

    def _remove_alarm(self, alarm_index):
        # Shift alarm indices
        for index in range(alarm_index, 3):
            self.alarms[index][_HOUR_IDX] = self.alarms[index + 1][_HOUR_IDX]
            self.alarms[index][_MIN_IDX] = self.alarms[index + 1][_MIN_IDX]
            self.alarms[index][_ENABLED_IDX] = self.alarms[index + 1][_ENABLED_IDX]
            self.pending_alarms[index] = self.pending_alarms[index + 1]

        # Set last alarm to default
        self.alarms[3][_HOUR_IDX] = 8
        self.alarms[3][_MIN_IDX] = 0
        self.alarms[3][_ENABLED_IDX] = 0

        self.page = _HOME_PAGE
        self.num_alarms -= 1
        self._write_alarms()
        self._draw()

    def _save_alarm(self):
        alarm = self.alarms[self.page]
        alarm[_HOUR_IDX] = self.hours_wid.value
        alarm[_MIN_IDX] = self.min_wid.value
        for day_idx, day_btn in enumerate(self.day_btns):
            if day_btn.state:
                alarm[_ENABLED_IDX] |= 1 << day_idx
            else:
                alarm[_ENABLED_IDX] &= ~(1 << day_idx)

        self.page = _HOME_PAGE

    def _write_alarms(self):
        try:
            with open("alarms.txt", "w") as f:
                for n in range(self.num_alarms):
                    al = self.alarms[n]
                    f.write(",".join(map(str, al)) + ";")
        except Exception:
            pass

    def _draw(self, update_alarm_row=-1):
        if self.page == _RINGING_PAGE:
            self._draw_ringing_page()
        elif self.page > _HOME_PAGE:
            self._draw_edit_page()
        else:
            self._draw_home_page(update_alarm_row)

    def _draw_ringing_page(self):
        draw = wasp.watch.drawable

        draw.set_color(_WHITE)
        draw.fill()

        draw.set_font(fonts.sans36)
        draw.string("{:02d}:{:02d}".format(self._ring_hh, self._ring_mm),
                    0, _TIME_Y, width=240)
        draw.blit(icon, _ICON_X, _ICON_Y)

        draw.set_color(_RED)
        draw.set_font(fonts.sans24)
        stop_w = fonts.width(fonts.sans24, 'STOP')
        draw.string('STOP', _UP_ARROW_X - stop_w // 2, _STOP_Y)

        draw.set_color(_YELLOW)
        # Width stays on the right half so the bg fill does not erase the
        # center line.
        draw.string('SNOOZE', 130, _SNOOZE_Y, width=106, right=True)

        self._arrow_up(draw, _UP_ARROW_X, _ARROW_ALIGN_Y, _ARROW_POINT_Y)
        self._arrow_down(draw, _DOWN_ARROW_X, _ARROW_ALIGN_Y, _ARROW_POINT_Y)

        # Drawn last so SNOOZE/STOP cannot wipe the divider.
        line_top = _ICON_Y + _ICON_H + 5
        draw.line(120, line_top, 120, 239, 1, _WHITE)

    @staticmethod
    def _arrow_up(draw, cx, y_tip, y_end):
        h = 32
        hw = 22
        for i in range(h):
            w = 1 + (hw * i) // h
            draw.fill(_WHITE, cx - w, y_tip + i, (2 * w) + 1, 1)
        draw.fill(_WHITE, cx - 4, y_tip + h - 2, 9, y_end - (y_tip + h - 2))

    @staticmethod
    def _arrow_down(draw, cx, y_top, y_tip):
        h = 32
        hw = 22
        y0 = y_tip - h
        for i in range(h):
            w = 1 + (hw * (h - 1 - i)) // h
            draw.fill(_WHITE, cx - w, y0 + i, (2 * w) + 1, 1)
        sh = y0 + 2 - y_top
        if sh > 0:
            draw.fill(_WHITE, cx - 4, y_top, 9, sh)

    def _draw_edit_page(self):
        draw = wasp.watch.drawable
        alarm = self.alarms[self.page]

        draw.fill()

        self.hours_wid.value = alarm[_HOUR_IDX]
        self.min_wid.value = alarm[_MIN_IDX]
        draw.set_font(fonts.sans28)
        draw.set_color(wasp.system.theme('bright'))
        draw.string(':', 160, 46, width=20)

        self.save_btn.update(_SAV_BG, _WHITE, _WHITE)
        self.del_alarm_btn.update(_DEL_BG, _WHITE, _WHITE)
        self.hours_wid.draw()
        self.min_wid.draw()
        for day_idx, day_btn in enumerate(self.day_btns):
            day_btn.state = alarm[_ENABLED_IDX] & (1 << day_idx)
            day_btn.draw()

    def _draw_home_page(self, update_alarm_row=_HOME_PAGE):
        draw = wasp.watch.drawable
        if update_alarm_row == _HOME_PAGE:
            draw.set_color(wasp.system.theme('bright'))
            draw.fill()
            self._draw_system_bar()
            draw.line(0, 50, 240, 50, width=1, color=wasp.system.theme('bright'))

        for index in range(len(self.alarms)):
            if index < self.num_alarms and (update_alarm_row == _HOME_PAGE or update_alarm_row == index):
                self._draw_alarm_row(index)
            elif index == self.num_alarms:
                # Draw the add button
                draw.set_color(wasp.system.theme('bright'))
                draw.set_font(fonts.sans28)
                draw.string('+', 100, 60 + (index * 45))

    def _draw_alarm_row(self, index):
        draw = wasp.watch.drawable
        alarm = self.alarms[index]

        self.alarm_checks[index].state = alarm[_ENABLED_IDX] & _IS_ACTIVE
        self.alarm_checks[index].draw()

        if self.alarm_checks[index].state:
            draw.set_color(wasp.system.theme('bright'))
        else:
            draw.set_color(wasp.system.theme('mid'))

        draw.set_font(fonts.sans28)
        draw.string("{:02d}:{:02d}".format(alarm[_HOUR_IDX], alarm[_MIN_IDX]), 10, 60 + (index * 45), width=120)

        draw.set_font(fonts.sans18)
        draw.string(self._get_repeat_code(alarm[_ENABLED_IDX]), 130, 70 + (index * 45), width=60)

        draw.line(0, 95 + (index * 45), 240, 95 + (index * 45), width=1, color=wasp.system.theme('bright'))

    def _draw_system_bar(self):
        sbar = wasp.system.bar
        sbar.clock = True
        sbar.draw()

    def _alert(self):
        self._snooze_at = 0.0
        now = wasp.watch.rtc.time()
        for i in range(self.num_alarms):
            pending = self.pending_alarms[i]
            if pending and pending <= now:
                self._ring_hh = self.alarms[i][_HOUR_IDX]
                self._ring_mm = self.alarms[i][_MIN_IDX]
                break
        self._ring_started = wasp.watch.rtc.uptime
        self.page = _RINGING_PAGE
        wasp.system.wake()
        wasp.system.switch(self)

    def _stop(self):
        if self._snooze_at:
            wasp.system.cancel_alarm(self._snooze_at, self._alert)
            self._snooze_at = 0.0
        self.page = _HOME_PAGE
        self._write_alarms()
        wasp.system.navigate(wasp.EventType.HOME)

    def _snooze(self):
        now = wasp.watch.rtc.get_localtime()
        when = time.mktime((now[0], now[1], now[2], now[3],
                            now[4] + _SNOOZE_MIN, now[5], 0, 0, 0))
        self._snooze_at = when
        wasp.system.set_alarm(when, self._alert)
        self.page = _HOME_PAGE
        wasp.system.navigate(wasp.EventType.HOME)

    def _set_pending_alarms(self):
        now = wasp.watch.rtc.get_localtime()
        for index, alarm in enumerate(self.alarms):
            if index < self.num_alarms and alarm[_ENABLED_IDX] & _IS_ACTIVE:
                yyyy = now[0]
                mm = now[1]
                dd = now[2]
                HH = alarm[_HOUR_IDX]
                MM = alarm[_MIN_IDX]

                # If next alarm is tomorrow increment the day
                if HH < now[3] or (HH == now[3] and MM <= now[4]):
                    dd += 1

                pending_time = time.mktime((yyyy, mm, dd, HH, MM, 0, 0, 0, 0))

                # If this is not a one time alarm find the next day of the week that is enabled
                if alarm[_ENABLED_IDX] & ~_IS_ACTIVE != 0:
                    for _i in range(7):
                        if (1 << time.localtime(pending_time)[6]) & alarm[_ENABLED_IDX] == 0:
                            dd += 1
                            pending_time = time.mktime((yyyy, mm, dd, HH, MM, 0, 0, 0, 0))
                        else:
                            break

                self.pending_alarms[index] = pending_time
                wasp.system.set_alarm(pending_time, self._alert)
            else:
                self.pending_alarms[index] = 0.0

    def _deactivate_pending_alarms(self):
        now = wasp.watch.rtc.get_localtime()
        now = time.mktime((now[0], now[1], now[2], now[3], now[4], now[5], 0, 0, 0))
        for index, alarm in enumerate(self.alarms):
            pending_alarm = self.pending_alarms[index]
            if not pending_alarm == 0.0:
                wasp.system.cancel_alarm(pending_alarm, self._alert)
                # If this is a one time alarm and in the past disable it
                if alarm[_ENABLED_IDX] & ~_IS_ACTIVE == 0 and pending_alarm <= now:
                    alarm[_ENABLED_IDX] = 0

    @staticmethod
    def _get_repeat_code(days):
        # Ignore the is_active bit
        days = days & ~_IS_ACTIVE

        if days == _WEEKDAYS:
            return "wkds"
        elif days == _WEEKENDS:
            return "wkns"
        elif days == _EVERY_DAY:
            return "evry"
        elif days == 0:
            return "once"
        else:
            return "cust"
