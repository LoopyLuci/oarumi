"""Version ordering, release parsing, and APK selection for update checks."""

from __future__ import annotations

from typing import Any

import pytest
from oarumi.updates import is_newer, parse_release, parse_version, pick_apk


@pytest.mark.parametrize(
    ("older", "newer"),
    [
        ("0.1.0-alpha.3", "0.1.0-alpha.4"),
        ("0.1.0-alpha.4", "0.1.0-beta.1"),
        ("0.1.0-beta.1", "0.1.0"),
        ("0.1.0-alpha.9", "0.1.0-alpha.10"),
        ("1.0.0-alpha", "1.0.0-alpha.1"),
        ("1.0.0-alpha.1", "1.0.0-alpha.beta"),
        ("0.1.0", "0.2.0"),
        ("v0.9.9", "v1.0.0"),
    ],
)
def test_orders_semver_versions(older: str, newer: str) -> None:
    assert is_newer(newer, older)
    assert not is_newer(older, newer)


def test_equal_versions_are_not_newer() -> None:
    assert not is_newer("v0.1.0-alpha.4", "0.1.0-alpha.4")


def test_all_ordering_operators_are_defined() -> None:
    older = parse_version("0.1.0-alpha.4")
    newer = parse_version("0.1.0")
    assert older < newer
    assert older <= newer
    assert newer > older
    assert newer >= older
    assert older <= parse_version("v0.1.0-alpha.4")
    assert not newer <= older


def test_leading_v_and_build_metadata_are_ignored() -> None:
    assert parse_version("v1.2.3+build.7") == parse_version("1.2.3")


def test_rejects_non_versions() -> None:
    with pytest.raises(ValueError):
        parse_version("latest")


def _release(names: list[str]) -> dict[str, Any]:
    return {
        "tag_name": "v0.1.0-alpha.4",
        "html_url": "https://github.com/LoopyLuci/oarumi/releases/tag/v0.1.0-alpha.4",
        "assets": [
            {
                "name": name,
                "browser_download_url": f"https://example.invalid/{name}",
                "size": 10,
                "digest": "sha256:" + "ab" * 32,
            }
            for name in names
        ],
    }


def test_picks_the_apk_for_the_running_flavor() -> None:
    release = parse_release(
        _release(
            [
                "oarumi-argos-release-0.1.0-alpha.4-phrasebook.apk",
                "oarumi-mlkit-release-0.1.0-alpha.4.apk",
                "SHA256SUMS",
            ]
        )
    )
    asset = pick_apk(release, "mlkit")
    assert asset is not None and asset.name == "oarumi-mlkit-release-0.1.0-alpha.4.apk"
    assert asset.sha256 == "ab" * 32


def test_no_apk_for_an_unknown_flavor() -> None:
    release = parse_release(_release(["oarumi-mlkit-release-0.1.0.apk"]))
    assert pick_apk(release, "argos") is None


def test_digest_is_optional() -> None:
    data = _release(["oarumi-mlkit-release-0.1.0.apk"])
    data["assets"][0].pop("digest")
    release = parse_release(data)
    asset = pick_apk(release, "mlkit")
    assert asset is not None and asset.sha256 is None


def test_python_package_version_maps_to_release_tag_form() -> None:
    from oarumi.updates import to_semver

    assert to_semver("0.1.0a4") == "0.1.0-alpha.4"
    assert to_semver("0.2.0") == "0.2.0"
    assert is_newer("v0.1.0-alpha.5", to_semver("0.1.0a4"))
