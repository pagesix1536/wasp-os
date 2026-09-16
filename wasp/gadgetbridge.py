# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson
"""Gadgetbridge/Bangle.js protocol

Currently implemented messages are:

 * t:"notify", id:int, src,title,subject,body,sender,tel:string - new
   notification (same id overwrites in place). The watch stores src,
   title, subject, body, sender only (clipped); tel and extras are
   dropped. At most 10 notes; a new id drops the oldest.
 * t:"notify-", id:int - ignored on this fork (issue #11): the watch
   keeps notifications until the user deletes them
 * t:"alarm", d:[{h,m},...] - set alarms
 * t:"find", n:bool - findDevice
 * t:"vibrate", n:int - vibrate
 * t:"weather", temp,hum,txt,wind,loc - weather report
 * t:"musicstate", state:"play/pause",position,shuffle,repeat - music
   play/pause/etc
 * t:"musicinfo", artist,album,track,dur,c(track count),n(track num) -
   currently playing music track
 * t:"call", cmd:"accept/incoming/outgoing/reject/start/end", name: "name", number: "+491234" - call

Watch → phone (via send_cmd):

 * t:"status", bat:0..100, volt:float, chg:0|1 - battery status
   (send_battery_status)
 * t:"music", n:play/pause/... - music transport (music player app)
 * t:"findPhone", n:bool - find phone (phone finder app)
"""

import io
import json
import sys
import wasp
import time

# JSON compatibility
null = None
true = True
false = False

def _info(msg):
    json.dump({'t': 'info', 'msg': msg}, sys.stdout)
    sys.stdout.write('\r\n')


def _error(msg):
    json.dump({'t': 'error', 'msg': msg}, sys.stdout)
    sys.stdout.write('\r\n')


def GB(cmd):
    task = cmd['t']
    del cmd['t']

    try:
        if task == 'find':
            wasp.watch.vibrator.pin(not cmd['n'])
        elif task == 'notify':
            id = cmd['id']
            del cmd['id']
            wasp.system.notify(id, cmd)
            wasp.watch.vibrator.pulse(ms=wasp.system.notify_duration)
        elif task == 'notify-':
            # Phone dismiss must not drop the watch copy (issue #11).
            pass
        elif task == 'musicstate':
            wasp.system.toggle_music(cmd)
        elif task == 'musicinfo':
            wasp.system.set_music_info(cmd)
        elif task == 'weather':
            wasp.system.set_weather_info(cmd)
        else:
            pass
            #_info('Command "{}" is not implemented'.format(cmd))
    except Exception as e:
        msg = io.StringIO()
        sys.print_exception(e, msg)
        _error(msg.getvalue())
        msg.close()

def _nus_ready():
    """True when a NUS notify is likely to succeed.

    ``watch.connected()`` is only GAP-connected. SoftDevice notify also
    needs the TX CCCD enabled (``uart_enabled``). Either flag can stay
    true for a while after the phone drops Bluetooth, so callers must
    still tolerate ``OSError`` from ``print()``.
    """
    connected = getattr(wasp.watch, 'connected', None)
    if not connected or not connected():
        return False
    enabled = getattr(wasp.watch, 'uart_enabled', None)
    if enabled is None:
        return True
    return bool(enabled())


def send_cmd(cmd = ''):
    """Write a Gadgetbridge JSON command to NUS.

    ``print()`` becomes a GATT notify. That raises ``OSError`` (SoftDevice
    ``0x08`` / ``NRF_ERROR_INVALID_STATE``) when the link looks up but
    notify is not actually possible. Never let that escape — music, phone
    finder, and the battery meter all sit on the UI path.
    """
    try:
        print('\r')
        for i in range(0, len(cmd), 20):
            print(cmd[i: i + 20], end='')
            time.sleep(0.2)
        print(' ')
        print(' ')
    except OSError:
        return


def send_battery_status(bat, chg, volt_mv=None):
    """Push battery status to Gadgetbridge if NUS notify is ready.

    Matches the Bangle.js → phone schema that Gadgetbridge handles as
    ``t:"status"`` (Espruino Gadgetbridge docs / BangleJSDeviceSupport):

    * ``bat`` — integer percent 0..100
    * ``volt`` — pack voltage in volts (float)
    * ``chg`` — ``1`` if charging, else ``0``

    :param bat: Battery percent
    :param chg: True/1 if charging, False/0 otherwise
    :param volt_mv: Optional millivolts; read from the fuel gauge if omitted
    """
    if not _nus_ready():
        return

    if volt_mv is None:
        volt_mv = wasp.watch.battery.voltage_mv()

    bat = int(bat)
    if bat < 0:
        bat = 0
    if bat > 100:
        bat = 100

    send_cmd('{"t":"status","bat":%d,"volt":%.3f,"chg":%d} ' % (
        bat, volt_mv / 1000, 1 if chg else 0))
