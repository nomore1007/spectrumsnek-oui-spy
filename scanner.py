"""Cross-platform terminal UI, with Linux BLE and NetworkManager Wi-Fi backends.

No packet injection or monitor-mode changes are performed. Wi-Fi results are
limited to access points NetworkManager can see; BLE results depend on BlueZ,
adapter support, permissions, and what devices advertise.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

PLUGIN_DIR = Path(__file__).resolve().parent
SIGNATURES_PATH = Path(os.environ.get("SPECTRUMSNEK_OUI_SPY_SIGNATURES", PLUGIN_DIR / "signatures.json"))


@dataclass
class Finding:
    seen_at: str
    transport: str
    address: str
    label: str
    detail: str
    signal: str = ""
    indicator: str = ""
    confidence: str = "unknown"


def load_signatures() -> Dict[str, Any]:
    try:
        with SIGNATURES_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("ble_company_ids", {})
        data.setdefault("mac_prefixes", {})
        return data
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not load signatures from {SIGNATURES_PATH}: {exc}", file=sys.stderr)
        return {"ble_company_ids": {}, "mac_prefixes": {}}


def normalize_mac(value: str) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", value).upper()


def match_mac(address: str, signatures: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    compact = normalize_mac(address)
    prefixes = signatures.get("mac_prefixes", {})
    for prefix, details in prefixes.items():
        normalized = normalize_mac(prefix)
        if normalized and compact.startswith(normalized):
            return details if isinstance(details, dict) else {"label": str(details)}
    return None


def match_company_ids(manufacturer_data: Dict[int, bytes], signatures: Dict[str, Any]):
    configured = signatures.get("ble_company_ids", {})
    for company_id in manufacturer_data:
        key = f"0x{int(company_id):04X}"
        details = configured.get(key)
        if details:
            return key, details
    return None, None


def timestamp() -> str:
    return time.strftime("%H:%M:%S")


def parse_nmcli_line(line: str):
    """Parse one nmcli terse row while respecting escaped colons."""
    fields = re.split(r"(?<!\\):", line)
    fields = [field.replace("\\:", ":").replace("\\\\", "\\") for field in fields]
    if len(fields) < 5:
        return None
    return fields[:5]


def scan_wifi_once(signatures: Dict[str, Any]) -> list[Finding]:
    """Read nearby APs using nmcli without changing connection state."""
    if not shutil.which("nmcli"):
        raise RuntimeError("nmcli not found; install NetworkManager or disable Wi-Fi scanning.")
    result = subprocess.run(
        ["nmcli", "--terse", "--escape", "yes", "--fields", "BSSID,SSID,SIGNAL,CHAN,SECURITY",
         "device", "wifi", "list", "--rescan", "yes"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or f"nmcli exited {result.returncode}"
        raise RuntimeError(message)
    findings = []
    for line in result.stdout.splitlines():
        fields = parse_nmcli_line(line)
        if fields is None:
            continue
        bssid, ssid, signal, channel, security = fields
        signature = match_mac(bssid, signatures)
        findings.append(Finding(
            timestamp(), "Wi-Fi", bssid, ssid or "<hidden SSID>",
            f"ch {channel} · {security or 'open'}",
            f"{signal}%", (signature or {}).get("label", ""),
            (signature or {}).get("confidence", "unknown"),
        ))
    return findings


async def scan_ble(signatures: Dict[str, Any], duration: float, emit) -> None:
    try:
        from bleak import BleakScanner
    except ImportError as exc:
        raise RuntimeError("BLE scanning needs bleak. Install it with: python3 -m pip install bleak") from exc

    seen = set()

    def on_device(device, advertisement):
        address = getattr(device, "address", "") or "unknown"
        name = getattr(device, "name", None) or getattr(advertisement, "local_name", None) or "<unnamed>"
        company_id, details = match_company_ids(
            getattr(advertisement, "manufacturer_data", {}) or {}, signatures
        )
        mac_match = match_mac(address, signatures)
        match = details or mac_match
        # Avoid flooding the terminal with repeat advertisements in one scan.
        key = (address.upper(), company_id or "", (match or {}).get("label", ""))
        if key in seen:
            return
        seen.add(key)
        manufacturer = ", ".join(
            f"0x{int(cid):04X}:{bytes(data).hex()}" for cid, data in
            (getattr(advertisement, "manufacturer_data", {}) or {}).items()
        )
        indicator = (match or {}).get("label", "")
        detail = f"RSSI {getattr(advertisement, 'rssi', '?')} dBm"
        if manufacturer:
            detail += f" · manufacturer data {manufacturer}"
        emit(Finding(
            timestamp(), "BLE", address, name, detail,
            f"{getattr(advertisement, 'rssi', '?')} dBm",
            indicator, (match or {}).get("confidence", "unknown"),
        ))

    scanner = BleakScanner(detection_callback=on_device)
    await scanner.start()
    try:
        await asyncio.sleep(duration)
    finally:
        await scanner.stop()


def format_finding(finding: Finding) -> str:
    marker = f"  ** {finding.indicator} [{finding.confidence} confidence]" if finding.indicator else ""
    return (f"{finding.seen_at} {finding.transport:<5} {finding.address:<17} "
            f"{finding.signal:<7} {finding.label[:24]:<24} {finding.detail}{marker}")


def main() -> bool:
    signatures = load_signatures()
    print("SpectrumSnek · OUI-Spy")
    print("Nearby wireless indicator scanner. Matches are clues, not attribution.")
    print("BLE: scan via BlueZ. Wi-Fi: list visible APs through NetworkManager.")
    print("Press Ctrl+C to stop. Wi-Fi scans may take several seconds.")
    print("-" * 100)
    print(f"Signature file: {SIGNATURES_PATH}")
    print("-" * 100)

    try:
        from bleak import BleakScanner  # noqa: F401
        ble_available = True
    except ImportError:
        ble_available = False
        print("BLE disabled: optional dependency 'bleak' is not installed.")
    wifi_available = bool(shutil.which("nmcli"))
    if not ble_available and not wifi_available:
        print("No supported scanner backend found. Install bleak and/or NetworkManager.", file=sys.stderr)
        return False

    def emit(finding: Finding) -> None:
        print(format_finding(finding), flush=True)

    async def loop():
        last_wifi = 0.0
        while True:
            tasks = []
            if ble_available:
                tasks.append(asyncio.create_task(scan_ble(signatures, 4.0, emit)))
            now = time.monotonic()
            if wifi_available and now - last_wifi >= 20:
                try:
                    for finding in scan_wifi_once(signatures):
                        emit(finding)
                except (RuntimeError, subprocess.TimeoutExpired) as exc:
                    print(f"Wi-Fi scan warning: {exc}", file=sys.stderr)
                last_wifi = time.monotonic()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=False)
            else:
                await asyncio.sleep(2)

    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        print("\nOUI-Spy stopped.")
    except Exception as exc:
        print(f"Scanner stopped: {exc}", file=sys.stderr)
        return False
    return True


if __name__ == "__main__":
    main()
