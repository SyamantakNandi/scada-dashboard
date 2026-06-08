"""
modbus_reader.py – Reads live Modbus data from all enabled PLC devices.
Device configs come from the SQLite database (managed by admin in-browser).
"""

import struct
from pymodbus.client.sync import ModbusTcpClient
import db


def decode_float(low: int, high: int) -> float:
    """Convert two 16-bit registers (little-endian) to a 32-bit float."""
    return struct.unpack('<f', struct.pack('<HH', low, high))[0]


def read_float(client: ModbusTcpClient, address: int, slave_id: int) -> float:
    try:
        response = client.read_holding_registers(
            address=address,
            count=2,
            unit=slave_id
        )
        if response.isError():
            return 0.0
        return decode_float(response.registers[0], response.registers[1])
    except Exception:
        return 0.0


def read_device(device: dict, params: list) -> dict:
    """
    Connect to a single PLC device and read all configured parameters.
    Returns a dict with 'connected', 'device_id', 'name', and one key per param.
    """
    result = {
        "device_id": device["id"],
        "name":      device["name"],
        "ip":        device["ip"],
        "slave_id":  device["slave_id"],
        "connected": False,
    }

    if not params:
        return result

    client = ModbusTcpClient(
        host=device["ip"],
        port=device["port"],
        timeout=3
    )

    try:
        if not client.connect():
            return result

        result["connected"] = True

        for p in params:
            try:
                val = read_float(client, p["address"], device["slave_id"])
                result[p["key"]] = round(float(val), 3)
            except Exception:
                result[p["key"]] = 0.0

    except Exception as e:
        print(f"[modbus] ERROR device {device['name']}: {e}")

    finally:
        client.close()

    return result


def read_all_devices() -> list:
    """Read every enabled PLC device from the database."""
    devices = db.get_all_devices()
    results = []
    for dev in devices:
        if not dev.get("enabled"):
            continue
        params = db.get_params_for_device(dev["id"])
        results.append(read_device(dev, params))
    return results
