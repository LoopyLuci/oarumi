"""The Android app's network config must keep its GitHub downloads on TLS."""

from __future__ import annotations

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
