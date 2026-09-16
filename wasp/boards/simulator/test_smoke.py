import pytest
import time
import wasp
import apps.test
import settings

def step():
    wasp.system._tick()
    wasp.machine.deepsleep()
    time.sleep(0.1)
wasp.system.step = step

wasp.watch.touch.press = wasp.watch.touch.i2c.sim.press
wasp.watch.touch.swipe = wasp.watch.touch.i2c.sim.swipe

wasp.system.secondary_init()
wasp.system.apps = {}
for app in wasp.system.quick_ring + wasp.system.launcher_ring:
    wasp.system.apps[app.NAME] = app

@pytest.fixture
def system():
    system = wasp.system
    if system.app != system.quick_ring[0]:
        system.switch(system.quick_ring[0])
    system.step()

    return system

def test_step(system):
    system.step()

def test_quick_ring(system):
    # wasp.toml autoload + register_defaults() (Steps is always quick-ring).
    names = [x.NAME for x in system.quick_ring]
    assert set(names) == {'Clock12h', 'Alarm', 'Steps'}

def test_launcher_ring(system):
    names = [x.NAME for x in system.launcher_ring]
    assert set(names) == {'Settings', 'Software'}

@pytest.mark.parametrize("name",
        ('Clock12h', 'Alarm', 'Steps', 'Settings', 'Software'))
def test_app(system, name):
    system.switch(system.apps[name])
    for i in range(4):
        system.step()
    system.switch(system.quick_ring[0])

def test_constructor(system, constructor):
    # Special case for the notification app
    if 'NotificationApp' in str(constructor):
         wasp.system.notify(wasp.watch.rtc.get_uptime_ms(),
             {
                 "src":"testcase",
                 "title":"A test",
                 "body":"This is a long message containingaverylongwordthatdoesnotfit and lots of other contents as well."
             })

    try:
        system.switch(constructor())
        system.step()
        system.step()
        wasp.watch.touch.press(120, 120)
        system.step()
        system.step()
        system.switch(system.quick_ring[0])
    except FileNotFoundError:
        # Some apps intend to generate exceptions during the constructor
        # if they don't have required files available
        if 'HaikuApp' not in str(constructor):
            raise
    finally:
        if 'NotificationApp' in str(constructor):
            wasp.system.notifications = {}

@pytest.mark.skip(reason='Stopclock (apps/stopwatch.py) is not in wasp.toml on this fork')
def test_stopwatch(system):
    system.switch(system.apps['Stopclock'])

    system.step()

    wasp.watch.button.value(0)
    system.step()
    assert(system.app._timer._started_at > 0)
    wasp.watch.button.value(1)

    system.step()
    system.step()
    system.step()

    wasp.watch.button.value(0)
    system.step()
    assert(system.app._timer._started_at == 0)
    wasp.watch.button.value(1)

    system.step()

def test_selftests(system):
    """Walk though each screen in the Self Test.

    This is a simple "does it crash" test and the only thing we do to stimulate
    the app is press in the centre of the screen. For most of the tests that
    will do something useful! For example it will run the benchmark for every
    one of the benchmark tests.
    """
    system.switch(apps.test.TestApp())
    system.step()

    start_point = system.app.test

    for i in range(len(system.app.tests)):
        wasp.watch.touch.press(120, 120)
        system.step()
        wasp.watch.touch.swipe('down')
        system.step()

    assert(start_point == system.app.test)

def test_selftest_crash(system):
    system.switch(apps.test.TestApp())
    system.step()

    def select(name):
        for i in range(len(system.app.tests)):
            if system.app.test == name:
                break
            wasp.watch.touch.swipe('down')
            system.step()
        assert system.app.test == name

    select('Crash')

    wasp.watch.button.value(0)
    with pytest.raises(Exception):
        system.step()

    # Get back to a safe state for the next test!
    try:
        wasp.watch.button.value(1)
        system.step()
    except:
        pass
    system.step()

def test_settings(system):
    """Walk though each screen in the setting application.

    This is a simple "does it crash" test and the only thing we do to stimulate
    the app is press in the centre of the screen.
    """
    system.switch(settings.SettingsApp())
    system.step()

    start_point = system.app._current_setting

    for i in range(len(system.app._settings)):
        wasp.watch.touch.press(120, 120)
        system.step()
        wasp.watch.touch.swipe('down')
        system.step()

    assert(start_point == system.app._current_setting)


def _seed_notes(system, n=3):
    system.notifications = {}
    for i in range(n):
        system.notify(i + 1, {
            'title': 'Note {}'.format(i + 1),
            'body': 'body {}'.format(i + 1),
        })


def test_notification_stays_until_deleted(system):
    _seed_notes(system, 2)
    system.switch(system.notifier)
    assert system.app is system.notifier
    assert system.app._index == 0
    assert list(system.notifications) == [1, 2]
    system.app.swipe((wasp.EventType.UP, 120, 120))
    assert system.app is system.quick_ring[0]
    assert list(system.notifications) == [1, 2]
    system.notifications = {}


def test_notification_swipe_walks_oldest_first(system):
    _seed_notes(system, 3)
    system.switch(system.notifier)
    assert system.app._index == 0
    system.app.swipe((wasp.EventType.DOWN, 120, 120))
    assert system.app._index == 1
    system.app.swipe((wasp.EventType.DOWN, 120, 120))
    assert system.app._index == 2
    system.app.swipe((wasp.EventType.DOWN, 120, 120))
    assert system.app._confirm and system.app._confirm.active
    system.app.swipe((wasp.EventType.UP, 120, 120))
    assert not system.app._confirm.active
    assert system.app._index == 2
    system.app.swipe((wasp.EventType.UP, 120, 120))
    assert system.app._index == 1
    system.switch(system.quick_ring[0])
    system.notifications = {}


def test_notification_cancel_restores_black(system):
    _seed_notes(system, 1)
    system.switch(system.notifier)
    system.app.swipe((wasp.EventType.LEFT, 120, 120))
    fills = []
    orig = wasp.watch.drawable.fill

    def wrap(bg=None, x=0, y=0, w=None, h=None):
        if bg is None:
            bg = wasp.watch.drawable._bgfg >> 16
        fills.append(bg)
        return orig(bg, x, y, w, h)

    wasp.watch.drawable.fill = wrap
    try:
        system.app.touch((wasp.EventType.TOUCH, 120, 182))  # Cancel
    finally:
        wasp.watch.drawable.fill = orig
    assert fills, 'expected a full-screen fill after Cancel'
    assert fills[0] == 0
    system.switch(system.quick_ring[0])
    system.notifications = {}


def test_notification_delete_this(system):
    _seed_notes(system, 3)
    system.switch(system.notifier)
    system.app.swipe((wasp.EventType.RIGHT, 120, 120))
    assert system.app._choice and system.app._choice.active
    # "This" button: (20, 100, 90, 45)
    system.app.touch((wasp.EventType.TOUCH, 65, 122))
    assert list(system.notifications) == [2, 3]
    assert system.app is system.notifier
    assert system.app._index == 0
    system.switch(system.quick_ring[0])
    system.notifications = {}


def test_notification_eviction_keeps_view_index(system):
    _seed_notes(system, 10)
    system.switch(system.notifier)
    system.app._index = 3
    system.notify(11, {'title': 'Note 11', 'body': 'body 11'})
    assert list(system.notifications) == [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert system.app._index == 2
    system.switch(system.quick_ring[0])
    system.notifications = {}


def test_notification_clear_all_from_end(system):
    _seed_notes(system, 1)
    system.switch(system.notifier)
    system.app.swipe((wasp.EventType.DOWN, 120, 120))
    assert system.app._confirm and system.app._confirm.active
    # "Yes" button: (20, 140, 90, 45)
    system.app.touch((wasp.EventType.TOUCH, 65, 162))
    assert system.notifications == {}
    assert system.app is system.quick_ring[0]
