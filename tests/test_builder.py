"""Tests for nxc/builder.py — build_command() and _append_global_flags()."""

import pytest

from nxc.builder import build_command
from nxc.config import create_default_config


def _cfg(**overrides) -> dict:
    """Return a default config with selected top-level keys overridden."""
    cfg = create_default_config()
    cfg.update(overrides)
    return cfg


def _cfg_gf(**global_flag_overrides) -> dict:
    """Return a default config with specific global_flags overridden."""
    cfg = create_default_config()
    cfg["global_flags"].update(global_flag_overrides)
    return cfg


# ---------------------------------------------------------------------------
# build_command — core argument construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "service, cfg_kwargs, expected",
    [
        # ── target ──────────────────────────────────────────────────────────────
        pytest.param(
            "smb",
            {"target": "10.0.0.1"},
            ["nxc", "smb", "10.0.0.1"],
            id="target-only",
        ),
        pytest.param(
            "ldap",
            {"target": "192.168.1.0/24"},
            ["nxc", "ldap", "192.168.1.0/24"],
            id="target-cidr",
        ),
        pytest.param(
            "smb",
            {},
            ["nxc", "smb"],
            id="no-target",
        ),
        # ── credentials ─────────────────────────────────────────────────────────
        pytest.param(
            "smb",
            {"target": "10.0.0.1", "username": "admin", "password": "pass"},
            ["nxc", "smb", "10.0.0.1", "-u", "admin", "-p", "pass"],
            id="username-password",
        ),
        pytest.param(
            "smb",
            {"target": "10.0.0.1", "username": "admin"},
            ["nxc", "smb", "10.0.0.1", "-u", "admin"],
            id="username-only",
        ),
        pytest.param(
            "smb",
            {"target": "10.0.0.1", "password": "secret"},
            ["nxc", "smb", "10.0.0.1", "-p", "secret"],
            id="password-only",
        ),
        pytest.param(
            "smb",
            {"target": "10.0.0.1", "username": None, "password": None},
            ["nxc", "smb", "10.0.0.1"],
            id="none-creds-omitted",
        ),
        pytest.param(
            "smb",
            {"target": "10.0.0.1", "username": "", "password": ""},
            ["nxc", "smb", "10.0.0.1", "-u", "", "-p", ""],
            id="empty-string-creds-included",
        ),
        pytest.param(
            "smb",
            {"target": "10.0.0.1", "username": "", "password": None},
            ["nxc", "smb", "10.0.0.1", "-u", ""],
            id="empty-username-none-password",
        ),
        # ── service flags ────────────────────────────────────────────────────────
        pytest.param(
            "smb",
            {
                "target": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "service_flags": {"smb": "--shares"},
            },
            ["nxc", "smb", "10.0.0.1", "-u", "admin", "-p", "pass", "--shares"],
            id="smb-service-flags",
        ),
        pytest.param(
            "ldap",
            {
                "target": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "service_flags": {"ldap": "--bloodhound -c All"},
            },
            [
                "nxc",
                "ldap",
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--bloodhound",
                "-c",
                "All",
            ],
            id="ldap-service-flags-multi-token",
        ),
        pytest.param(
            "smb",
            {
                "target": "10.0.0.1",
                "service_flags": {"smb": "--shares", "ldap": "--bloodhound"},
            },
            ["nxc", "smb", "10.0.0.1", "--shares"],
            id="only-current-service-flags-applied",
        ),
        # ── different services ───────────────────────────────────────────────────
        pytest.param(
            "winrm",
            {"target": "10.0.0.1", "username": "user", "password": "pw"},
            ["nxc", "winrm", "10.0.0.1", "-u", "user", "-p", "pw"],
            id="winrm-service",
        ),
        pytest.param(
            "ssh",
            {"target": "10.0.0.1", "username": "root"},
            ["nxc", "ssh", "10.0.0.1", "-u", "root"],
            id="ssh-service",
        ),
    ],
)
def test_build_command_core(service, cfg_kwargs, expected):
    cfg = _cfg(**cfg_kwargs)
    assert build_command(service, cfg) == expected


# ---------------------------------------------------------------------------
# build_command — global flags forwarded to nxc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "global_flags, expected_tail",
    [
        pytest.param(
            {"threads": 10},
            ["-t", "10"],
            id="threads",
        ),
        pytest.param(
            {"timeout": 30},
            ["--timeout", "30"],
            id="timeout",
        ),
        pytest.param(
            {"jitter": "0-2"},
            ["--jitter", "0-2"],
            id="jitter",
        ),
        pytest.param(
            {"verbose": True},
            ["--verbose"],
            id="verbose",
        ),
        pytest.param(
            {"debug": True},
            ["--debug"],
            id="debug",
        ),
        pytest.param(
            {"no_progress": True},
            ["--no-progress"],
            id="no-progress",
        ),
        pytest.param(
            {"continue_on_success": True},
            ["--continue-on-success"],
            id="continue-on-success",
        ),
        pytest.param(
            {"no_bruteforce": True},
            ["--no-bruteforce"],
            id="no-bruteforce",
        ),
        pytest.param(
            {"kerberos": True},
            ["-k"],
            id="kerberos",
        ),
        pytest.param(
            {"use_kcache": True},
            ["--use-kcache"],
            id="use-kcache",
        ),
        pytest.param(
            {"hash": "aad3b435b51404eeaad3b435b51404ee:HASH"},
            ["-H", "aad3b435b51404eeaad3b435b51404ee:HASH"],
            id="hash",
        ),
        pytest.param(
            {"ipv6": True},
            ["-6"],
            id="ipv6",
        ),
        pytest.param(
            {"dns_server": "8.8.8.8"},
            ["--dns-server", "8.8.8.8"],
            id="dns-server",
        ),
        pytest.param(
            {"dns_tcp": True},
            ["--dns-tcp"],
            id="dns-tcp",
        ),
        pytest.param(
            {"dns_timeout": 5},
            ["--dns-timeout", "5"],
            id="dns-timeout",
        ),
        pytest.param(
            {"gfail_limit": 3},
            ["--gfail-limit", "3"],
            id="gfail-limit",
        ),
        pytest.param(
            {"ufail_limit": 5},
            ["--ufail-limit", "5"],
            id="ufail-limit",
        ),
        pytest.param(
            {"fail_limit": 2},
            ["--fail-limit", "2"],
            id="fail-limit",
        ),
        pytest.param(
            {"aes_key": "abc123"},
            ["--aesKey", "abc123"],
            id="aes-key",
        ),
        pytest.param(
            {"kdc_host": "dc01.corp.local"},
            ["--kdcHost", "dc01.corp.local"],
            id="kdc-host",
        ),
        pytest.param(
            {"module": "mimikatz"},
            ["-M", "mimikatz"],
            id="module",
        ),
        pytest.param(
            {"module_options": "COMMAND=sekurlsa::logonpasswords"},
            ["-o", "COMMAND=sekurlsa::logonpasswords"],
            id="module-options",
        ),
        pytest.param(
            {"log": "/tmp/scan.log"},
            ["--log", "/tmp/scan.log"],
            id="log",
        ),
        pytest.param(
            {"pfx_cert": "cert.pfx"},
            ["--pfx-cert", "cert.pfx"],
            id="pfx-cert",
        ),
        pytest.param(
            {"pem_cert": "cert.pem", "pem_key": "key.pem"},
            ["--pem-cert", "cert.pem", "--pem-key", "key.pem"],
            id="pem-cert-and-key",
        ),
    ],
)
def test_build_command_global_flags(global_flags, expected_tail):
    cfg = _cfg_gf(**global_flags)
    cfg["target"] = "10.0.0.1"
    cmd = build_command("smb", cfg)
    assert cmd[:3] == ["nxc", "smb", "10.0.0.1"]
    for token in expected_tail:
        assert token in cmd, f"{token!r} not found in {cmd}"
    # Verify ordering: all expected_tail tokens appear contiguously in order
    joined = " ".join(cmd)
    assert " ".join(expected_tail) in joined


def test_build_command_false_flags_omitted():
    """Boolean global flags that are False must not appear in the command."""
    cfg = create_default_config()
    cfg["target"] = "10.0.0.1"
    cmd = build_command("smb", cfg)
    for flag in (
        "--verbose",
        "--debug",
        "--no-progress",
        "-k",
        "--use-kcache",
        "-6",
        "--dns-tcp",
        "--continue-on-success",
        "--no-bruteforce",
        "--ignore-pw-decoding",
    ):
        assert flag not in cmd, f"{flag!r} should be absent when False/None"


def test_build_command_none_flags_omitted():
    """None-valued global flags must not appear in the command."""
    cfg = create_default_config()
    cfg["target"] = "10.0.0.1"
    cmd = build_command("smb", cfg)
    for flag in (
        "-t",
        "--timeout",
        "--jitter",
        "-H",
        "--log",
        "--dns-server",
        "--dns-timeout",
        "--gfail-limit",
        "--ufail-limit",
        "--fail-limit",
        "--aesKey",
        "--kdcHost",
        "-M",
        "-o",
    ):
        assert flag not in cmd, f"{flag!r} should be absent when None"
