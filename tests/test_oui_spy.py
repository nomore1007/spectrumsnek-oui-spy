import unittest

try:
    from scanner import DeviceRegistry, Finding, match_company_ids, match_mac, normalize_mac, parse_nmcli_line
except ImportError:
    from plugins.oui_spy.scanner import DeviceRegistry, Finding, match_company_ids, match_mac, normalize_mac, parse_nmcli_line


class SignatureMatchingTests(unittest.TestCase):
    def test_normalize_mac(self):
        self.assertEqual(normalize_mac("aa:bb-cc.dd:ee:ff"), "AABBCCDDEEFF")

    def test_mac_prefix_matches_with_mixed_separators(self):
        signatures = {"mac_prefixes": {"AA:BB:CC": {"label": "example", "confidence": "low"}}}
        self.assertEqual(match_mac("aa-bb-cc-11-22-33", signatures)["label"], "example")

    def test_unmatched_mac_returns_none(self):
        self.assertIsNone(match_mac("00:11:22:33:44:55", {"mac_prefixes": {}}))

    def test_ble_company_id_match(self):
        signatures = {"ble_company_ids": {"0x09C8": {"label": "research indicator"}}}
        key, details = match_company_ids({0x09C8: b"\x01\x02"}, signatures)
        self.assertEqual(key, "0x09C8")
        self.assertEqual(details["label"], "research indicator")

    def test_nmcli_parser_preserves_bssid_and_colon_in_ssid(self):
        row = r"AA\:BB\:CC\:DD\:EE\:FF:Lobby\:Guest:78:11:WPA2"
        self.assertEqual(
            parse_nmcli_line(row),
            ["AA:BB:CC:DD:EE:FF", "Lobby:Guest", "78", "11", "WPA2"],
        )

    def test_nmcli_parser_ignores_malformed_row(self):
        self.assertIsNone(parse_nmcli_line("not:a:complete:row"))

    def test_unmatched_company_id(self):
        key, details = match_company_ids({0xFFFF: b"x"}, {"ble_company_ids": {}})
        self.assertIsNone(key)
        self.assertIsNone(details)


class DeviceRegistryTests(unittest.TestCase):
    def test_device_is_retained_until_stale_timeout(self):
        registry = DeviceRegistry(stale_after=60)
        finding = Finding("12:00:00", "BLE", "AA:BB", "sensor", "RSSI -50 dBm")
        registry.update(finding, now=100)
        self.assertEqual(len(registry.snapshot(now=159.9)), 1)
        self.assertEqual(len(registry.snapshot(now=160)), 0)

    def test_repeated_observation_refreshes_device(self):
        registry = DeviceRegistry(stale_after=60)
        first = Finding("12:00:00", "BLE", "AA:BB", "sensor", "RSSI -50 dBm")
        refreshed = Finding("12:00:30", "BLE", "AA:BB", "sensor", "RSSI -45 dBm")
        registry.update(first, now=100)
        registry.update(refreshed, now=150)
        devices = registry.snapshot(now=209)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0][0].detail, "RSSI -45 dBm")

    def test_same_address_on_different_transports_is_separate(self):
        registry = DeviceRegistry()
        registry.update(Finding("12:00:00", "BLE", "AA:BB", "device", ""), now=100)
        registry.update(Finding("12:00:00", "Wi-Fi", "AA:BB", "network", ""), now=100)
        self.assertEqual(len(registry.snapshot(now=100)), 2)


if __name__ == "__main__":
    unittest.main()
