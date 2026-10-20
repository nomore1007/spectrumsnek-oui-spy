# SpectrumSnek OUI-Spy

A Linux-native wireless indicator scanner plugin for [SpectrumSnek](https://github.com/nomore1007/spectrumsnek). It observes nearby Bluetooth Low Energy advertisements and Wi-Fi access points, then compares available identifiers with a local signature file.

**A match is a research indicator, not proof of a device's identity or ownership.**

## Features

- Live, refreshed device table instead of an accumulating event log.
- Devices are refreshed when seen again and removed after **60 seconds without an observation**.
- BLE advertisement scanning through BlueZ using the optional `bleak` package.
- Visible Wi-Fi access-point listing through NetworkManager's `nmcli`.
- Configurable BLE company-ID and MAC-prefix signatures in `signatures.json`.
- Confidence labels for configured indicators.

## Install in SpectrumSnek

From the SpectrumSnek checkout:

```bash
git clone https://github.com/nomore1007/spectrumsnek-oui-spy.git plugins/oui_spy
python3 -m pip install -r plugins/oui_spy/requirements.txt
```

Use the same Python environment that runs SpectrumSnek. The plugin exposes `MODULE_INFO`, `get_module_info()`, and a no-required-arguments `run()` entry point for the current shared plugin-discovery/menu system. It should appear in the normal installed-plugins menu when installed under `plugins/oui_spy`.

Required system components depend on the scan mode:
- BLE: Linux, BlueZ, a working Bluetooth adapter, and Python package `bleak`.
- Wi-Fi AP listing: NetworkManager and `nmcli`.

Wi-Fi scanning lists access points and does **not** identify every Wi-Fi client. It does not enable monitor mode, capture raw 802.11 traffic, or actively probe devices.

## Run

From the SpectrumSnek repository root, the plugin can be launched through the shared menu or directly:

```bash
python3 plugin_menu.py --run oui_spy
# Or, for direct testing:
python3 -m plugins.oui_spy
```

Press **Q** or **Esc** to exit the live dashboard.

Set `SPECTRUMSNEK_OUI_SPY_SIGNATURES=/path/to/signatures.json` to use a custom signature file.

## Signature format

- `ble_company_ids`: keys such as `0x09C8`, mapped to metadata such as `label`, `confidence`, `source`, and `note`.
- `mac_prefixes`: MAC prefixes with or without separators, mapped to similar metadata.

The included `0x09C8` XUNTONG entry is a **low-confidence research indicator**, not a verified Flock Safety identifier. The upstream curated lists are not bundled. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for project references, attribution, and data provenance policy.

## Limitations and responsible interpretation

- BLE addresses may rotate, and advertisements may omit manufacturer data.
- Signal visibility depends on adapter, driver, permissions, and operating-system behavior.
- Company IDs and MAC prefixes can be shared by unrelated devices.
- The one-minute falloff is based on the most recent observation; a device that stops advertising or disappears from Wi-Fi scan results will age out.
- Wi-Fi results are nearby access points, not associated client devices.
- Do not treat a signature match as definitive attribution. Validate findings independently.

## Tests

From the plugin directory:

```bash
python3 -m unittest discover -s tests
```

## License and credits

The SpectrumSnek implementation is MIT licensed; see `LICENSE.txt`. Third-party project and research references are documented in `THIRD_PARTY_NOTICES.md`. No upstream source code or curated OUI lists are included.
