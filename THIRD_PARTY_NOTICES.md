# Third-Party Notices

This file tracks upstream projects, research, and data considered for the SpectrumSnek OUI-Spy plugin. It must be updated whenever upstream code, databases, documentation, or other materials are incorporated. Preserve all upstream copyright notices, author names, research credits, and license text in any redistributed derivative.

## Upstream projects

### OUI-SPY
- Project: OUI-SPY firmware ecosystem
- Author/maintainer credited upstream: `colonelpanichacks`
- Repository: https://github.com/colonelpanichacks/oui-spy
- Intended relevance: project overview and links to the related firmware projects.
- Reuse status: reference only; no upstream code copied into SpectrumSnek.

### OUI-SPY Unified Blue
- Project: unified ESP32 BLE/Wi-Fi detector firmware
- Author/maintainer credited upstream: `colonelpanichacks`
- Repository: https://github.com/colonelpanichacks/oui-spy-unified-blue
- Intended relevance: detection modes, matching concepts, and project architecture as technical references.
- Reuse status: reference only; no upstream code copied into SpectrumSnek.
- License review: a conventional license file was not found at the repository's `LICENSE` path during this review. Confirm the applicable license with the upstream maintainer before copying or adapting code.

### OUI-SPY Detector
- Project: targeted BLE/Wi-Fi OUI and MAC detector
- Author/maintainer credited upstream: `colonelpanichacks`
- Repository: https://github.com/colonelpanichacks/ouispy-detector
- Intended relevance: OUI/MAC matching, categorized signatures, and detection behavior as technical references.
- Reuse status: reference only; no upstream code or OUI list copied into SpectrumSnek.
- License review: a conventional license file was not found at the repository's `LICENSE` path during this review. The README describes the project as open source and welcomes modifications, but that wording alone does not specify redistribution permissions. Confirm the applicable license with the upstream maintainer before copying or adapting code or curated data.

### Flock-You
- Repository: https://github.com/colonelpanichacks/flock-you
- Intended relevance: related Flock Safety detection research and methods.
- Reuse status: not yet incorporated. Review its license and preserve all source notices and research credits before reuse.

### Flock-You fork and research credited by OUI-SPY Unified
- Researcher: Will Greenberg (`@wgreenberg`)
- Repository credited upstream: https://github.com/wgreenberg/flock-you
- Upstream acknowledgment: Unified Blue credits this work for improving Flock Safety detection heuristics and identifies the BLE manufacturer company ID method `0x09C8` (XUNTONG) as sourced from that work.
- Reuse status: acknowledgment recorded; no code copied.

### Flock Safety Wi-Fi OUI research credited by OUI-SPY Detector
- Researcher credited upstream: ØяĐöØцяöЪöяцฐ (`@NitekryDPaul`)
- Source reference: https://github.com/colonelpanichacks/ouispy-detector/blob/main/ouis.md
- Upstream acknowledgment: the OUI list credits this researcher for identifying prefixes through 2.4 GHz promiscuous-mode analysis, including an address-1 receiver detection technique.
- Reuse status: acknowledgment recorded; no OUI list copied.

## Other registries and references named upstream

The OUI-SPY Detector documentation says its signatures are cross-verified against:
- IEEE Registration Authority OUI registry: https://standards.ieee.org/products-services/regauth/oui/index.html
- Bluetooth SIG assigned numbers: https://www.bluetooth.com/specifications/assigned-numbers/
- `lnxgod/friendorfoe`: https://github.com/lnxgod/friendorfoe

These are source references, not a claim that their data or code has been copied into SpectrumSnek. Check the relevant terms and preserve provenance if data is imported.

## Reuse and attribution policy

1. Keep all upstream copyright headers, license files, author credits, and research acknowledgments intact when redistributing reused material.
2. Record the exact upstream repository, file or dataset, commit/revision, license, and local destination for every copied or adapted component.
3. Do not treat attribution by itself as a substitute for a license. Where a repository does not specify reuse terms, seek permission or implement the behavior independently from documented facts and appropriately licensed/public registry data.
4. Label detection signatures as research indicators, not proof that a particular device or organization is present. Document uncertainty and likely false positives.
5. Update this file before merging any new upstream-derived code or data.


## SpectrumSnek OUI-Spy implementation status

The initial Linux/Python plugin under `plugins/oui_spy/` was implemented independently for SpectrumSnek. It does not include copied upstream source files or curated OUI datasets. Its small starter signature for BLE company ID `0x09C8` is explicitly labeled a low-confidence research indicator and links back to the upstream credit above. The generic signature-matching code is project-authored; any future imported signature must record its exact source, revision, license/terms, and attribution here before inclusion.
