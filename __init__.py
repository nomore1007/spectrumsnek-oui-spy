"""Linux-native OUI-Spy plugin for SpectrumSnek."""
from typing import Any, Dict


MODULE_INFO = {
    "name": "🕵️ OUI-Spy",
    "description": "Watch nearby BLE advertisements and Wi-Fi access points for configurable MAC/OUI indicators",
    "version": "0.1.0",
    "author": "SpectrumSnek; see THIRD_PARTY_NOTICES.md for research credits",
    "category": "wireless",
    "capabilities": ["Bluetooth Low Energy scan", "Wi-Fi access-point scan via NetworkManager", "configurable local signatures"],
}


def get_module_info() -> Dict[str, Any]:
    """Return metadata used by SpectrumSnek's plugin loader."""
    return MODULE_INFO


def run(*args, **kwargs):
    """Run the interactive scanner."""
    from .scanner import main
    return main()


if __name__ == "__main__":
    run()
