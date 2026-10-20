"""OUI-Spy live dashboard with Linux BLE and NetworkManager Wi-Fi backends.

The display is a current-device table, not an event log. Devices disappear after
60 seconds without being observed. Wi-Fi results are access points visible to
NetworkManager; this is not a Wi-Fi client detector.
"""
from __future__ import annotations

import asyncio
import curses
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

PLUGIN_DIR = Path(__file__).resolve().parent
SIGNATURES_PATH = Path(os.environ.get("SPECTRUMSNEK_OUI_SPY_SIGNATURES", PLUGIN_DIR / "signatures.json"))
STALE_AFTER_SECONDS = 60.0
WIFI_SCAN_INTERVAL = 20.0


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


class DeviceRegistry:
    """Thread-safe latest-observation table keyed by transport and address."""

    def __init__(self, stale_after: float = STALE_AFTER_SECONDS):
        self.stale_after = stale_after
        self._devices: Dict[tuple[str, str], tuple[Finding, float]] = {}
        self._lock = threading.Lock()

    def update(self, finding: Finding, now: Optional[float] = None) -> None:
        observed = time.monotonic() if now is None else now
        key = (finding.transport.casefold(), finding.address.casefold())
        with self._lock:
            self._devices[key] = (finding, observed)

    def snapshot(self, now: Optional[float] = None) -> list[tuple[Finding, float]]:
        current = time.monotonic() if now is None else now
        with self._lock:
            stale = [
                key for key, (_, observed) in self._devices.items()
                if current - observed >= self.stale_after
            ]
            for key in stale:
                del self._devices[key]
            return sorted(
                self._devices.values(),
                key=lambda item: item[1],
                reverse=True,
            )


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
    for prefix, details in signatures.get("mac_prefixes", {}).items():
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
    fields = re.split(r"(?<!\\\\):", line)
    fields = [field.replace(r"\\:", ":").replace(r"\\\\", "\\\\") for field in fields]
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

    def on_device(device, advertisement):
        address = getattr(device, "address", "") or "unknown"
        name = getattr(device, "name", None) or getattr(advertisement, "local_name", None) or "<unnamed>"
        manufacturer_data = getattr(advertisement, "manufacturer_data", {}) or {}
        _, company_details = match_company_ids(manufacturer_data, signatures)
        mac_match = match_mac(address, signatures)
        match = company_details or mac_match
        manufacturer = ", ".join(
            f"0x{int(cid):04X}:{bytes(data).hex()}"
            for cid, data in manufacturer_data.items()
        )
        rssi = getattr(advertisement, "rssi", "?")
        detail = f"RSSI {rssi} dBm"
        if manufacturer:
            detail += f" · manufacturer data {manufacturer}"
        emit(Finding(
            timestamp(), "BLE", address, name, detail, f"{rssi} dBm",
            (match or {}).get("label", ""),
            (match or {}).get("confidence", "unknown"),
        ))

    scanner = BleakScanner(detection_callback=on_device)
    await scanner.start()
    try:
        await asyncio.sleep(duration)
    finally:
        await scanner.stop()


def _clip(value: Any, width: int) -> str:
    text = str(value).replace("\\n", " ").replace("\\r", " ")
    return text if len(text) <= width else text[:max(0, width - 1)] + "…"


def _safe_addstr(window, y: int, x: int, text: str, attr: int = 0) -> None:
    try:
        height, width = window.getmaxyx()
        if 0 <= y < height and x < width:
            window.addnstr(y, max(0, x), text, max(0, width - max(0, x) - 1), attr)
    except curses.error:
        pass


def dashboard(stdscr, registry: DeviceRegistry, stop_event: threading.Event,
              status: Dict[str, str], status_lock: threading.Lock) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    while not stop_event.is_set():
        try:
            key = stdscr.getch()
            if key in (ord("q"), ord("Q"), 27):
                stop_event.set()
                break
            devices = registry.snapshot()
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            _safe_addstr(stdscr, 0, 0, "SpectrumSnek · OUI-Spy  |  LIVE DEVICES", curses.A_BOLD)
            _safe_addstr(stdscr, 1, 0, f"{len(devices)} device(s) seen in the last {int(STALE_AFTER_SECONDS)} seconds")
            _safe_addstr(stdscr, 2, 0, "Matches are research indicators, not proof of identity or ownership.")
            if width >= 80:
                header = f"{'LAST SEEN':<10} {'TYPE':<6} {'ADDRESS':<19} {'SIGNAL':<9} {'NAME / SSID':<25} INDICATOR"
            else:
                header = "LAST SEEN  TYPE   ADDRESS            SIGNAL   NAME / SSID"
            _safe_addstr(stdscr, 4, 0, header, curses.A_UNDERLINE | curses.A_BOLD)
            if height > 7 and not devices:
                _safe_addstr(stdscr, 6, 0, "Scanning… waiting for nearby advertisements / access points.")
            for row, (finding, observed) in enumerate(devices, start=5):
                if row >= height - 2:
                    break
                age = max(0, int(time.monotonic() - observed))
                seen = f"{age}s ago"
                if width >= 80:
                    line = (f"{seen:<10} {finding.transport:<6} "
                            f"{_clip(finding.address, 18):<19} {_clip(finding.signal, 8):<9} "
                            f"{_clip(finding.label, 24):<25} {_clip(finding.indicator or '—', 30)}")
                else:
                    line = (f"{seen:<10} {finding.transport:<6} "
                            f"{_clip(finding.address, 18):<19} {_clip(finding.signal, 8):<9} "
                            f"{_clip(finding.label, max(8, width - 47))}")
                attr = curses.A_BOLD if finding.indicator else curses.A_NORMAL
                _safe_addstr(stdscr, row, 0, line, attr)
            with status_lock:
                messages = list(status.values())
            _safe_addstr(stdscr, height - 2, 0, _clip(" | ".join(messages), max(1, width - 1)))
            _safe_addstr(stdscr, height - 1, 0, "Q / Esc: quit", curses.A_DIM)
            stdscr.refresh()
            time.sleep(0.5)
        except KeyboardInterrupt:
            stop_event.set()
            break


def main() -> bool:
    signatures = load_signatures()
    try:
        from bleak import BleakScanner  # noqa: F401
        ble_available = True
    except ImportError:
        ble_available = False
    wifi_available = bool(shutil.which("nmcli"))
    if not ble_available and not wifi_available:
        print("No supported scanner backend found. Install bleak and/or NetworkManager.", file=sys.stderr)
        return False

    registry = DeviceRegistry()
    stop_event = threading.Event()
    status_lock = threading.Lock()
    status: Dict[str, str] = {}
    if not ble_available:
        status["ble"] = "BLE disabled: install bleak"
    if not wifi_available:
        status["wifi"] = "Wi-Fi disabled: nmcli unavailable"

    def emit(finding: Finding) -> None:
        registry.update(finding)

    async def scanner_loop() -> None:
        async def ble_loop() -> None:
            while not stop_event.is_set():
                try:
                    await scan_ble(signatures, 4.0, emit)
                    with status_lock:
                        status.pop("ble_error", None)
                except Exception as exc:
                    with status_lock:
                        status["ble_error"] = f"BLE: {exc}"
                    await asyncio.sleep(2.0)

        async def wifi_loop() -> None:
            while not stop_event.is_set():
                try:
                    findings = await asyncio.to_thread(scan_wifi_once, signatures)
                    for finding in findings:
                        emit(finding)
                    with status_lock:
                        status.pop("wifi_error", None)
                except Exception as exc:
                    with status_lock:
                        status["wifi_error"] = f"Wi-Fi: {exc}"
                # Sleep in short increments so Q/Esc stops the worker promptly.
                for _ in range(int(WIFI_SCAN_INTERVAL * 2)):
                    if stop_event.is_set():
                        break
                    await asyncio.sleep(0.5)

        tasks = []
        if ble_available:
            tasks.append(asyncio.create_task(ble_loop()))
        if wifi_available:
            tasks.append(asyncio.create_task(wifi_loop()))
        await asyncio.gather(*tasks)

    def worker() -> None:
        try:
            asyncio.run(scanner_loop())
        except Exception as exc:
            with status_lock:
                status["scanner_error"] = f"Scanner stopped: {exc}"
            stop_event.set()

    thread = threading.Thread(target=worker, name="oui-spy-scanner", daemon=True)
    thread.start()
    try:
        curses.wrapper(dashboard, registry, stop_event, status, status_lock)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        stop_event.set()
        thread.join(timeout=2.0)
    return True


if __name__ == "__main__":
    main()
