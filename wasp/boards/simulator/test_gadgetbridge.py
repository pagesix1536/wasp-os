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


def test_battery_meter_draw_survives_notify_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError('Can not notify attribute value. status: 0x08')

    monkeypatch.setattr(wasp.watch, 'connected', lambda: True)
    monkeypatch.setattr(wasp.watch, 'uart_enabled', lambda: True)
    monkeypatch.setattr(gadgetbridge, 'send_battery_status', boom)
    meter = widgets.BatteryMeter()
    meter.draw()
