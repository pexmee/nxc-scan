"""Tests for nxc/services.py — parse_services()."""

import pytest

from nxc.services import ALL_SERVICES, parse_services


@pytest.mark.parametrize(
    "selection, expected",
    [
        # ── everything ───────────────────────────────────────────────────────────
        pytest.param("all", ALL_SERVICES, id="all-keyword"),
        pytest.param("ALL", ALL_SERVICES, id="all-keyword-upper"),
        pytest.param("*", ALL_SERVICES, id="star"),
        pytest.param("", ALL_SERVICES, id="empty-string"),
        # ── single items ─────────────────────────────────────────────────────────
        pytest.param("smb", ["smb"], id="single-name"),
        pytest.param("ldap", ["ldap"], id="single-name-ldap"),
        pytest.param("1", ["ldap"], id="single-index-1"),
        pytest.param("10", ["smb"], id="single-index-10"),
        # ── comma-separated names ────────────────────────────────────────────────
        pytest.param("smb,ldap", ["ldap", "smb"], id="two-names-sorted-by-index"),
        pytest.param("ssh,winrm", ["winrm", "ssh"], id="two-names-index-order"),
        # ── comma-separated indices ───────────────────────────────────────────────
        pytest.param(
            "1,3,5",
            [ALL_SERVICES[0], ALL_SERVICES[2], ALL_SERVICES[4]],
            id="explicit-indices",
        ),
        # ── ranges ───────────────────────────────────────────────────────────────
        pytest.param("1-3", ["ldap", "wmi", "mssql"], id="range-1-3"),
        pytest.param("8-10", ["ssh", "nfs", "smb"], id="range-8-10"),
        # ── exclusions ───────────────────────────────────────────────────────────
        pytest.param(
            "-smb", [s for s in ALL_SERVICES if s != "smb"], id="exclude-smb-by-name"
        ),
        pytest.param(
            "-10", [s for s in ALL_SERVICES if s != "smb"], id="exclude-smb-by-index"
        ),
        pytest.param(
            "-ldap", [s for s in ALL_SERVICES if s != "ldap"], id="exclude-ldap"
        ),
        # ── mixed include + exclude ───────────────────────────────────────────────
        pytest.param("1-3,-2", ["ldap", "mssql"], id="range-minus-one"),
    ],
)
def test_parse_services(selection, expected):
    assert parse_services(selection) == expected


def test_parse_services_preserves_index_order():
    result = parse_services("smb,ldap,ssh")
    indices = [ALL_SERVICES.index(s) for s in result]
    assert indices == sorted(indices), (
        "Services must be returned in ALL_SERVICES index order"
    )


def test_parse_services_out_of_range_index_ignored():
    # "99" is out of range so nothing ends up in include; the function treats
    # this the same as "all" (empty include → full set minus excludes).
    result = parse_services("99")
    assert result == ALL_SERVICES


def test_parse_services_unknown_name_ignored():
    result = parse_services("ldap,nonexistent")
    assert result == ["ldap"]
