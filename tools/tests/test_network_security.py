"""The Android app must pin the certificates of the hosts it downloads from."""

from __future__ import annotations

import base64
import binascii
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "android" / "app" / "src" / "main"
CONFIG = APP / "res" / "xml" / "network_security_config.xml"
MANIFEST = APP / "AndroidManifest.xml"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def _domain_config() -> ET.Element:
    root = ET.parse(CONFIG).getroot()
    configs = root.findall("domain-config")
    assert len(configs) == 1
    return configs[0]


def test_manifest_points_at_the_config() -> None:
    application = ET.parse(MANIFEST).getroot().find("application")
    assert application is not None
    assert application.get(f"{ANDROID_NS}networkSecurityConfig") == "@xml/network_security_config"


def test_config_covers_the_download_hosts() -> None:
    domains = {domain.text for domain in _domain_config().findall("domain")}
    assert {"github.com", "githubusercontent.com"} <= domains


def test_config_cleartext_is_refused() -> None:
    assert _domain_config().get("cleartextTrafficPermitted") == "false"


def test_pins_are_sha256_digests_and_expire() -> None:
    pin_set = _domain_config().find("pin-set")
    assert pin_set is not None
    assert pin_set.get("expiration"), "pins must expire so they get reviewed"
    pins = pin_set.findall("pin")
    assert pins
    for pin in pins:
        assert pin.get("digest") == "SHA-256"
        try:
            digest = base64.b64decode(pin.text or "", validate=True)
        except binascii.Error:
            raise AssertionError(f"pin is not base64: {pin.text!r}") from None
        assert len(digest) == 32
