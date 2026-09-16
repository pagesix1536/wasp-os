# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Pager applications
~~~~~~~~~~~~~~~~~~~~~

The pager shows a long text message one screen at a time (crash dumps,
haiku, …). Pull-down notifications are a separate list UI
(:py:class:`NotificationApp`).
"""

import wasp
import fonts
import icons

import io
import sys

class PagerApp():
    """Show a long text message in a pager."""
    NAME = 'Pager'
    ICON = icons.app

    def __init__(self, msg):
        self._msg = msg
        self._scroll = wasp.widgets.ScrollIndicator()

    def foreground(self):
        """Activate the application."""
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)
        self._redraw()

    def background(self):
        """De-activate the application."""
        self._chunks = None
        self._numpages = None

    def swipe(self, event):
        """Swipe to page up/down."""
        if event[0] == wasp.EventType.UP:
            if self._page >= self._numpages:
                wasp.system.navigate(wasp.EventType.BACK)
                return
            self._page += 1
        else:
            if self._page <= 0:
                wasp.watch.vibrator.pulse()
                return
            self._page -= 1
        self._draw()

    def _redraw(self):
        """Redraw from scratch (jump to the first page)"""
        self._page = 0
        self._chunks = wasp.watch.drawable.wrap(self._msg, 240)
        self._numpages = (len(self._chunks) - 2) // 9
        self._draw()

    def _draw(self):
        """Draw a page from scratch."""
        mute = wasp.watch.display.mute
        draw = wasp.watch.drawable

        mute(True)
        draw.set_color(0xffff)
        draw.fill()

        page = self._page
        i = page * 9
        j = i + 11
        chunks = self._chunks[i:j]
        for i in range(len(chunks)-1):
            sub = self._msg[chunks[i]:chunks[i+1]].rstrip()
            draw.string(sub, 0, 24*i)

        scroll = self._scroll
        scroll.up = page > 0
        scroll.down = page < self._numpages
        scroll.draw()

        mute(False)

class NotificationApp():
    """Pull-down notification list (issue #11).

    Oldest first. Viewing does not delete. Swipe down for the next item
    (past the last: clear-all Yes/No). Swipe up for the previous item
    (from the first: watch face). Left/right: This / All / Cancel.
    Bodies are truncated to one screen. Gadgetbridge ``notify-`` does
    not remove entries.
    """
    NAME = 'Notifications'

    def __init__(self):
        self._index = 0
        self._choice = None
        self._confirm = None

    def foreground(self):
        self._index = 0
        wasp.system.request_event(
            wasp.EventMask.TOUCH |
            wasp.EventMask.SWIPE_UPDOWN |
            wasp.EventMask.SWIPE_LEFTRIGHT)
        self._draw()

    def background(self):
        self._choice = None
        self._confirm = None

    def note_arrived(self):
        """Redraw if a notify/unnotify happens while this app is showing."""
        if self._prompt_active():
            return
        self._draw()

    def swipe(self, event):
        if self._prompt_active():
            self._dismiss_prompt()
            self._draw()
            return

        direction = event[0]
        if direction == wasp.EventType.DOWN:
            n = len(wasp.system.notifications)
            if n == 0:
                wasp.system.navigate(wasp.EventType.BACK)
                return
            if self._index + 1 >= n:
                if not self._confirm:
                    self._confirm = wasp.widgets.ConfirmationView()
                self._confirm.draw('Clear all?')
                return
            self._index += 1
            self._draw()
        elif direction == wasp.EventType.UP:
            if self._index <= 0:
                wasp.system.navigate(wasp.EventType.BACK)
                return
            self._index -= 1
            self._draw()
        elif direction == wasp.EventType.LEFT or direction == wasp.EventType.RIGHT:
            if not self._choice:
                self._choice = wasp.widgets.ChoiceView()
            self._choice.draw('Delete?')

    def touch(self, event):
        if self._choice and self._choice.touch(event):
            v = self._choice.value
            if v == 'this':
                self._delete_current()
            elif v == 'all':
                self._clear_all()
            else:
                self._draw()
            return

        if self._confirm and self._confirm.touch(event):
            if self._confirm.value:
                self._clear_all()
            else:
                self._draw()

    def _prompt_active(self):
        return ((self._choice and self._choice.active) or
                (self._confirm and self._confirm.active))

    def _dismiss_prompt(self):
        if self._choice:
            self._choice.active = False
        if self._confirm:
            self._confirm.active = False

    def _delete_current(self):
        ids = list(wasp.system.notifications)
        if ids:
            del wasp.system.notifications[ids[self._index]]
        if not wasp.system.notifications:
            wasp.system.navigate(wasp.EventType.BACK)
            return
        self._draw()

    def _clear_all(self):
        wasp.system.notifications = {}
        wasp.system.navigate(wasp.EventType.BACK)

    def _draw(self):
        notes = wasp.system.notifications
        ids = list(notes)
        n = len(ids)
        if n == 0:
            wasp.system.navigate(wasp.EventType.BACK)
            return
        if self._index >= n:
            self._index = n - 1
        if self._index < 0:
            self._index = 0

        note = notes[ids[self._index]]
        title = note['title'] if 'title' in note else 'Untitled'
        body = note['body'] if 'body' in note else ''

        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute
        mute(True)
        # Buttons leave the drawable bg as UI blue; reset before fill.
        draw.reset()
        draw.fill()

        draw.set_color(wasp.system.theme('mid'))
        draw.string('{} of {}'.format(self._index + 1, n), 0, 4, width=240)

        draw.set_color(wasp.system.theme('bright'))
        y = 32
        chunks = draw.wrap(title, 240)
        if len(chunks) > 1:
            draw.string(title[chunks[0]:chunks[1]].rstrip(), 0, y, width=240)
        y += 28

        if body:
            chunks = draw.wrap(body, 240)
            nlines = len(chunks) - 1
            i = 0
            while i < nlines and y + 24 <= 240:
                draw.string(body[chunks[i]:chunks[i + 1]].rstrip(), 0, y)
                y += 24
                i += 1

        mute(False)

class CrashApp():
    """Crash handler application.

    This application is launched automatically whenever another
    application crashes. Our main job it to indicate as loudly as
    possible that the system is no longer running correctly. This
    app deliberately enables inverted video mode in order to deliver
    that message as strongly as possible.
    """
    def __init__(self, exc):
        """Capture the exception information.

        This app does not actually display the exception information
        but we need to capture the exception info before we leave
        the except block.
        """
        msg = io.StringIO()
        sys.print_exception(exc, msg)
        self._msg = msg.getvalue()
        msg.close()

    def foreground(self):
        """Indicate the system has crashed by drawing a couple of bomb icons.

        If you owned an Atari ST back in the mid-eighties then I hope you
        recognise this as a tribute a long forgotten home computer!
        """
        wasp.watch.display.invert(False)
        draw = wasp.watch.drawable
        draw.blit(icons.bomb, 0, 104)
        draw.blit(icons.bomb, 32, 104)

        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.SWIPE_LEFTRIGHT)

    def background(self):
        """Restore a normal display mode.

        Conceal the display before the transition otherwise the inverted
        bombs get noticed by the user.
        """
        wasp.watch.display.mute(True)
        wasp.watch.display.invert(True)

    def swipe(self, event):
        """Show the exception message in a pager."""
        wasp.system.switch(PagerApp(self._msg))
