"""Gadgetbridge outbound battery status must never crash the UI."""
import gadgetbridge
import wasp
import widgets


def test_send_cmd_swallows_oserror(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError('Can not notify attribute value. status: 0x08')

    monkeypatch.setattr('builtins.print', boom)
    gadgetbridge.send_cmd('{"t":"status","bat":50,"volt":3.900,"chg":0} ')


def test_send_battery_skips_when_disconnected(monkeypatch):
    sent = []
    monkeypatch.setattr(wasp.watch, 'connected', lambda: False)
    monkeypatch.setattr(wasp.watch, 'uart_enabled', lambda: True)
    monkeypatch.setattr(gadgetbridge, 'send_cmd', lambda cmd: sent.append(cmd))
    gadgetbridge.send_battery_status(50, False, volt_mv=3900)
    assert sent == []


def test_send_battery_skips_when_cccd_off(monkeypatch):
    sent = []
    monkeypatch.setattr(wasp.watch, 'connected', lambda: True)
    monkeypatch.setattr(wasp.watch, 'uart_enabled', lambda: False)
    monkeypatch.setattr(gadgetbridge, 'send_cmd', lambda cmd: sent.append(cmd))
    gadgetbridge.send_battery_status(50, False, volt_mv=3900)
    assert sent == []


def test_send_battery_sends_when_nus_ready(monkeypatch):
    sent = []
    monkeypatch.setattr(wasp.watch, 'connected', lambda: True)
    monkeypatch.setattr(wasp.watch, 'uart_enabled', lambda: True)
    monkeypatch.setattr(gadgetbridge, 'send_cmd', lambda cmd: sent.append(cmd))
    gadgetbridge.send_battery_status(50, True, volt_mv=4100)
    assert len(sent) == 1
    assert '"t":"status"' in sent[0]
    assert '"bat":50' in sent[0]
    assert '"chg":1' in sent[0]


def test_notify_minus_does_not_unnotify():
    wasp.system.notifications = {}
    wasp.system.notify(7, {'title': 'Keep', 'body': 'me'})
    gadgetbridge.GB({'t': 'notify-', 'id': 7})
    assert 7 in wasp.system.notifications
    assert wasp.system.notifications[7]['title'] == 'Keep'
    wasp.system.notifications = {}


def test_notify_same_id_overwrites():
    wasp.system.notifications = {}
    wasp.system.notify(3, {'title': 'A', 'body': 'one'})
    gadgetbridge.GB({
        't': 'notify',
        'id': 3,
        'title': 'B',
        'body': 'two',
    })
    assert list(wasp.system.notifications) == [3]
    assert wasp.system.notifications[3]['title'] == 'B'
    wasp.system.notifications = {}


def test_notify_trims_unused_fields():
    wasp.system.notifications = {}
    wasp.system.notify(1, {
        'title': 'Alice',
        'body': 'hi',
        'src': 'SMS',
        'sender': 'Alice',
        'subject': '',
        'tel': '+1555',
        'reply': True,
        'act': [{'title': 'X', 'hash': 1}],
        'img': 'AAAA' * 40,
    })
    note = wasp.system.notifications[1]
    assert note['title'] == 'Alice'
    assert note['src'] == 'SMS'
    assert note['sender'] == 'Alice'
    assert 'subject' not in note
    assert 'tel' not in note
    assert 'reply' not in note
    assert 'act' not in note
    assert 'img' not in note
    wasp.system.notifications = {}


def test_notify_clips_long_body():
    wasp.system.notifications = {}
    wasp.system.notify(1, {'title': 'T', 'body': 'x' * 500})
    assert len(wasp.system.notifications[1]['body']) == 192
    wasp.system.notifications = {}


def test_notify_cap_drops_oldest():
    wasp.system.notifications = {}
    for i in range(1, 12):
        wasp.system.notify(i, {'title': str(i), 'body': 'x'})
    assert list(wasp.system.notifications) == list(range(2, 12))
    wasp.system.notifications = {}


def test_notify_same_id_does_not_evict():
    wasp.system.notifications = {}
    for i in range(1, 11):
        wasp.system.notify(i, {'title': str(i), 'body': 'x'})
    wasp.system.notify(5, {'title': 'upd', 'body': 'y'})
    assert list(wasp.system.notifications) == list(range(1, 11))
    assert wasp.system.notifications[5]['title'] == 'upd'
    wasp.system.notifications = {}


def test_battery_meter_draw_survives_notify_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError('Can not notify attribute value. status: 0x08')

    monkeypatch.setattr(wasp.watch, 'connected', lambda: True)
    monkeypatch.setattr(wasp.watch, 'uart_enabled', lambda: True)
    monkeypatch.setattr(gadgetbridge, 'send_battery_status', boom)
    meter = widgets.BatteryMeter()
    meter.draw()
