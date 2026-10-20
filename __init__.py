"""Linux-native OUI-Spy live dashboard plugin for SpectrumSnek."""
from typing import Any, Dict


MODULE_INFO = {
    "name": "🕵️ OUI-Spy",
    "description": "Live BLE and Wi-Fi access-point dashboard with one-minute stale-device expiry",
    "version": "0.2.0",
    "author": "SpectrumSnek; see THIRD_PARTY_NOTICES.md for research credits",
    "category": "wireless",
    "capabilities": [
        "Bluetooth Low Energy scan",
        "Wi-Fi access-point scan via NetworkManager",
        "configurable local signatures",
        "live current-device table with 60-second falloff",
    ],
}


def get_module_info() -> Dict[str, Any]:
    """Return metadata used by SpectrumSnek's shared plugin-discovery menu."""
    return MODULE_INFO


def run(*args, **kwargs):
    """Entry point used by SpectrumSnek's plugin launcher."""
    from .scanner import main
    return main()


if __name__ == "__main__":
    run()
