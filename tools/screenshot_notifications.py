#!/usr/bin/env python3
"""Screenshot the pull-down notification list (issue #11).

Writes under /tmp/wasp-notifications/. Does not run the SDL event loop.
"""
import os

import wasp
import display

OUT_DIR = '/tmp/wasp-notifications'


def seed():
    wasp.system.notifications = {}
    wasp.system.notify(1, {
        'title': 'Alice',
        'body': 'Want to grab lunch after the meeting?',
    })
    wasp.system.notify(2, {
        'title': 'Work chat',
        'body': 'PR #11 is ready for another look when you have a minute.',
    })
    wasp.system.notify(3, {
        'title': 'A very long title that will not fit on one line of the watch',
        'body': (
            'This body is intentionally long so truncation is visible. '
            'Line two of wrapping. Line three. Line four. Line five. '
            'Line six. Line seven. Line eight. Line nine. Line ten. '
            'This tail should not appear on the screen at all.'
        ),
    })


def shot(name):
    path = os.path.join(OUT_DIR, name)
    display.window.refresh()
    display.save_image(display.windowsurface, path)
    print('wrote', path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    wasp.system.secondary_init()
    seed()

    wasp.system.switch(wasp.system.notifier)
    shot('notifications-1-of-3.png')

    wasp.system.app.swipe((wasp.EventType.DOWN, 120, 120))
    shot('notifications-2-of-3.png')

    wasp.system.app.swipe((wasp.EventType.DOWN, 120, 120))
    shot('notifications-3-of-3-truncated.png')

    wasp.system.app.swipe((wasp.EventType.LEFT, 120, 120))
    shot('notifications-delete-choice.png')

    wasp.system.app.touch((wasp.EventType.TOUCH, 120, 182))  # Cancel
    shot('notifications-after-cancel.png')

    wasp.system.app.swipe((wasp.EventType.DOWN, 120, 120))
    shot('notifications-clear-all.png')

    wasp.system.app.touch((wasp.EventType.TOUCH, 175, 162))  # No
    shot('notifications-after-no.png')


if __name__ == '__main__':
    main()
