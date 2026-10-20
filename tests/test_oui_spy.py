import unittest

try:
    from scanner import match_company_ids, match_mac, normalize_mac, parse_nmcli_line
except ImportError:
    from plugins.oui_spy.scanner import match_company_ids, match_mac, normalize_mac, parse_nmcli_line


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


if __name__ == "__main__":
    unittest.main()
