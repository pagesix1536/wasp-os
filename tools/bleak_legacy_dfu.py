#!/usr/bin/env python3
"""Nordic Legacy DFU (SDK <=11) via bleak — for InfiniTime recovery OTA on modern BlueZ.

Mirrors the protocol used by tools/ota-dfu (gatttool-based), which often fails
GATT discovery on Fedora/BlueZ 5.8x.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import struct
import sys
import time
import zipfile
from pathlib import Path

from bleak import BleakClient, BleakScanner

UUID_CONTROL = "00001531-1212-efde-1523-785feabcd123"
UUID_PACKET = "00001532-1212-efde-1523-785feabcd123"
UUID_VERSION = "00001534-1212-efde-1523-785feabcd123"

# Opcodes
START_DFU = 0x01
INIT_DFU = 0x02
RECEIVE_FW = 0x03
VALIDATE = 0x04
ACTIVATE_RESET = 0x05
PRN_REQUEST = 0x08
RESPONSE = 0x10
PKT_RECEIPT = 0x11

RESP_SUCCESS = 0x01


def unpack_zip(zip_path: Path) -> tuple[bytes, bytes]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        bins = [n for n in names if n.lower().endswith(".bin")]
        dats = [n for n in names if n.lower().endswith(".dat")]
        if not bins or not dats:
            raise SystemExit(f"zip missing .bin/.dat: {names}")
        return zf.read(bins[0]), zf.read(dats[0])


class LegacyDfu:
    def __init__(self, client: BleakClient, image: bytes, init_pkt: bytes, prn: int = 10):
        self.client = client
        self.image = image
        self.init_pkt = init_pkt
        self.prn = prn
        self._notify_q: asyncio.Queue[bytes] = asyncio.Queue()
        self.pkt_size = 20

    def _on_notify(self, _handle: int, data: bytearray):
        self._notify_q.put_nowait(bytes(data))

    async def _wait_notify(self, timeout: float = 60.0) -> bytes:
        return await asyncio.wait_for(self._notify_q.get(), timeout=timeout)

    async def _cmd(self, *payload: int):
        await self.client.write_gatt_char(UUID_CONTROL, bytes(payload), response=True)

    async def _data(self, chunk: bytes):
        # write without response on packet characteristic
        await self.client.write_gatt_char(UUID_PACKET, chunk, response=False)

    async def _expect_response(self, procedure: int, timeout: float = 120.0):
        while True:
            data = await self._wait_notify(timeout=timeout)
            if not data:
                continue
            if data[0] == RESPONSE:
                proc, res = data[1], data[2]
                name = {START_DFU: "START", INIT_DFU: "INIT", RECEIVE_FW: "RECV",
                        VALIDATE: "VALIDATE", ACTIVATE_RESET: "ACTIVATE"}.get(proc, hex(proc))
                if res != RESP_SUCCESS:
                    raise RuntimeError(f"DFU error proc={name} res=0x{res:02x} raw={data.hex()}")
                if proc == procedure:
                    return data
            elif data[0] == PKT_RECEIPT:
                # receipt of bytes received
                if len(data) >= 5:
                    return data

    async def run(self):
        # Drain any stale notifications
        while not self._notify_q.empty():
            self._notify_q.get_nowait()

        print("Enabling control-point notifications...")
        await self.client.start_notify(UUID_CONTROL, self._on_notify)
        await asyncio.sleep(0.2)

        try:
            ver = await self.client.read_gatt_char(UUID_VERSION)
            print(f"DFU revision characteristic: {ver.hex()}")
        except Exception as e:
            print(f"(version read skipped: {e})")

        print("START_DFU (application)...")
        await self._cmd(START_DFU, 0x04)
        # InfiniTime/Nordic: 4B softdevice + 4B bootloader + 4B application (all LE)
        # ota-dfu zero-pads 8 bytes *before* the app size.
        size_pkt = b"\x00" * 8 + struct.pack("<I", len(self.image))
        print(f"Size packet: {size_pkt.hex()} (app={len(self.image)})")
        await self._data(size_pkt)
        print("Waiting for size ACK...")
        await self._expect_response(START_DFU)

        print("INIT_DFU start...")
        await self._cmd(INIT_DFU, 0x00)
        # init packet may be small (14 bytes for Nordic)
        for i in range(0, len(self.init_pkt), self.pkt_size):
            await self._data(self.init_pkt[i : i + self.pkt_size])
            await asyncio.sleep(0.01)
        print("INIT_DFU complete (erase)...")
        await self._cmd(INIT_DFU, 0x01)
        await self._expect_response(INIT_DFU, timeout=180.0)

        # PRN: Nordic/Adafruit want opcode + uint16 LE.
        # InfiniTime only reads the low byte (om_data[1]) — still fine.
        prn = max(1, min(self.prn if self.prn > 0 else 10, 255))
        use_prn = True
        print(f"Setting PRN interval = {prn} (uint16 LE)")
        await self._cmd(PRN_REQUEST, prn & 0xFF, (prn >> 8) & 0xFF)
        await asyncio.sleep(0.2)
        # Drain PRN response if any (Adafruit may send NOT_SUPPORTED)
        while not self._notify_q.empty():
            data = self._notify_q.get_nowait()
            print(f"(post-PRN notify: {data.hex()})")
            if data[:1] == bytes([RESPONSE]) and len(data) >= 3 and data[1] == PRN_REQUEST:
                if data[2] != RESP_SUCCESS:
                    print("PRN not supported by bootloader; using timed transfer only")
                    use_prn = False
        self._use_prn = use_prn

        print("RECEIVE_FIRMWARE_IMAGE...")
        await self._cmd(RECEIVE_FW)
        await asyncio.sleep(0.3)
        while not self._notify_q.empty():
            data = self._notify_q.get_nowait()
            print(f"(post-RECEIVE notify: {data.hex()})")
            if data[:1] == bytes([RESPONSE]) and len(data) >= 3 and data[1] == RECEIVE_FW and data[2] != RESP_SUCCESS:
                raise RuntimeError(f"RECEIVE_FW rejected: {data.hex()}")

        total = len(self.image)
        segments = int(math.ceil(total / float(self.pkt_size)))
        t0 = time.time()
        sent_segments = 0
        inter_pkt = 0.008
        prn = max(1, min(self.prn if self.prn > 0 else 10, 255))
        use_prn = getattr(self, "_use_prn", True)
        print(f"Uploading {total} bytes ({segments} segments), PRN={'on' if use_prn else 'off'}, every {prn}, throttle={inter_pkt*1000:.0f}ms...")

        for off in range(0, total, self.pkt_size):
            chunk = self.image[off : off + self.pkt_size]
            await self._data(chunk)
            sent_segments += 1
            await asyncio.sleep(inter_pkt)

            if sent_segments == segments:
                pct = 100.0
                print(f"\r[{'#' * 50}] {pct:5.1f}%", end="", flush=True)
                last = self.image[(segments - 1) * self.pkt_size :]
                for attempt in range(1, 8):
                    print(f"\nWaiting for image complete ACK (try {attempt}, last chunk {len(last)}B)...")
                    try:
                        await self._expect_response(RECEIVE_FW, timeout=10.0)
                        break
                    except TimeoutError:
                        print(f"Resending last chunk ({len(last)} bytes)...")
                        await self._data(last)
                        await asyncio.sleep(0.08)
                else:
                    print("Final wait for complete ACK...")
                    await self._expect_response(RECEIVE_FW, timeout=90.0)
            elif use_prn and (sent_segments % prn) == 0:
                try:
                    data = await self._wait_notify(timeout=15.0)
                except TimeoutError:
                    print("\nPRN timeout; switching to timed transfer")
                    use_prn = False
                    continue
                if data[0] == PKT_RECEIPT and len(data) >= 5:
                    receipt = struct.unpack_from("<I", data, 1)[0]
                elif data[0] == RESPONSE:
                    if data[2] != RESP_SUCCESS:
                        raise RuntimeError(f"error mid-transfer: {data.hex()}")
                    receipt = sent_segments * self.pkt_size
                else:
                    receipt = sent_segments * self.pkt_size
                pct = min(100.0, 100.0 * receipt / total)
                filled = int(pct // 2)
                print(f"\r[{'#' * filled}{'.' * (50 - filled)}] {pct:5.1f}% ({receipt}/{total})", end="", flush=True)
            elif (not use_prn) and (sent_segments % 100 == 0):
                receipt = min(total, sent_segments * self.pkt_size)
                pct = min(100.0, 100.0 * receipt / total)
                filled = int(pct // 2)
                print(f"\r[{'#' * filled}{'.' * (50 - filled)}] {pct:5.1f}%", end="", flush=True)

        dur = time.time() - t0
        print(f"\nUpload finished in {int(dur // 60)}m {int(dur % 60)}s")

        print("VALIDATE_FIRMWARE...")
        await self._cmd(VALIDATE)
        await self._expect_response(VALIDATE, timeout=120.0)
        print("Validate OK")

        await asyncio.sleep(1.0)
        print("ACTIVATE_IMAGE_AND_RESET...")
        try:
            await self._cmd(ACTIVATE_RESET)
        except Exception as e:
            # Device often disconnects immediately on activate
            print(f"(activate write ended: {e})")
        print("Done — watch should reboot into the new image.")


async def async_main(args):
    image, init_pkt = unpack_zip(Path(args.zip))
    print(f"Image: {len(image)} bytes, init: {len(init_pkt)} bytes")

    address = args.address
    if not address:
        print("Scanning for InfiniTime...")
        devices = await BleakScanner.discover(timeout=12.0)
        for d in devices:
            if d.name and "infini" in d.name.lower():
                address = d.address
                print(f"Found {d.name} @ {address}")
                break
        if not address:
            raise SystemExit("No InfiniTime found; pass --address")

    print(f"Connecting to {address}...")
    async with BleakClient(address, timeout=40.0) as client:
        if not client.is_connected:
            raise SystemExit("Connect failed")
        # Confirm DFU service
        uuids = [str(s.uuid).lower() for s in client.services]
        if "00001530-1212-efde-1523-785feabcd123" not in uuids:
            print("Services present:", uuids)
            raise SystemExit("Nordic DFU service 0x1530 not found")
        dfu = LegacyDfu(client, image, init_pkt, prn=args.prn)
        await dfu.run()


def main():
    p = argparse.ArgumentParser(description="Bleak Nordic Legacy DFU for InfiniTime")
    p.add_argument("-z", "--zip", required=True, help="DFU zip (bin+dat)")
    p.add_argument("-a", "--address", help="BLE MAC (optional if InfiniTime is advertising)")
    p.add_argument("--prn", type=int, default=10, help="Packet receipt interval (default 10)")
    args = p.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
