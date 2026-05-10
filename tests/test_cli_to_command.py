"""Tests for the full CLI-args → nxc command pipeline.

Each test parses a CLI argument list through build_arg_parser(), applies the
same config-building logic that main() uses, then calls build_command() and
checks the resulting argv without ever spawning a real process.
"""

import pytest

from nxc.builder import build_command
from nxc.cli import build_arg_parser, extract_global_flags, extract_service_flags
from nxc.config import create_default_config


def _parse_and_build(cli_args: list[str], service: str) -> list[str]:
    """Simulate main()'s config pipeline for a single service."""
    parser = build_arg_parser()
    args = parser.parse_args(cli_args)

    cfg = create_default_config()

    for attr, key in [
        ("target", "target"),
        ("username", "username"),
        ("password", "password"),
        ("services", "services"),
        ("service_timeout", "service_timeout"),
    ]:
        val = getattr(args, attr)
        if val is not None:
            cfg[key] = val

    for k, v in extract_global_flags(args).items():
        if v is not None:
            cfg["global_flags"][k] = v

    for svc, flags in extract_service_flags(args).items():
        if flags is not None:
            cfg["service_flags"][svc] = flags

    return build_command(service, cfg)


# ---------------------------------------------------------------------------
# Core credential / target combinations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cli_args, service, expected_cmd",
    [
        pytest.param(
            ["10.0.0.1", "-s", "smb"],
            "smb",
            ["nxc", "smb", "10.0.0.1"],
            id="target-no-creds",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "-s", "smb"],
            "smb",
            ["nxc", "smb", "10.0.0.1", "-u", "admin", "-p", "pass"],
            id="target-user-pass",
        ),
        pytest.param(
            ["10.0.0.1", "--username", "admin", "--password", "pass", "-s", "smb"],
            "smb",
            ["nxc", "smb", "10.0.0.1", "-u", "admin", "-p", "pass"],
            id="target-user-pass-long-form",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-s", "smb"],
            "smb",
            ["nxc", "smb", "10.0.0.1", "-u", "admin"],
            id="username-only-no-password",
        ),
        pytest.param(
            # Empty credentials must be forwarded, not dropped
            ["10.0.0.1", "-u", "", "-p", "", "-s", "smb"],
            "smb",
            ["nxc", "smb", "10.0.0.1", "-u", "", "-p", ""],
            id="empty-string-credentials",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "users.txt", "-p", "passwords.txt", "-s", "ldap"],
            "ldap",
            ["nxc", "ldap", "10.0.0.1", "-u", "users.txt", "-p", "passwords.txt"],
            id="file-based-credentials",
        ),
        pytest.param(
            ["192.168.1.0/24", "-u", "admin", "-p", "pass", "-s", "winrm"],
            "winrm",
            ["nxc", "winrm", "192.168.1.0/24", "-u", "admin", "-p", "pass"],
            id="cidr-target",
        ),
    ],
)
def test_core_credentials(cli_args, service, expected_cmd):
    assert _parse_and_build(cli_args, service) == expected_cmd


# ---------------------------------------------------------------------------
# Per-service flags
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cli_args, service, expected_tail",
    [
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--smb-flags=--shares",
                "-s",
                "smb",
            ],
            "smb",
            ["--shares"],
            id="smb-shares",
        ),
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--ldap-flags=--bloodhound -c All",
                "-s",
                "ldap",
            ],
            "ldap",
            ["--bloodhound", "-c", "All"],
            id="ldap-bloodhound",
        ),
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--ssh-flags=-x 'id && hostname'",
                "-s",
                "ssh",
            ],
            "ssh",
            ["-x", "id && hostname"],
            id="ssh-exec",
        ),
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "sa",
                "-p",
                "sa",
                "--mssql-flags=-q 'SELECT @@version'",
                "-s",
                "mssql",
            ],
            "mssql",
            ["-q", "SELECT @@version"],
            id="mssql-query",
        ),
        pytest.param(
            # Service flags for *other* services must not bleed into this service's cmd
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--ldap-flags=--bloodhound -c All",
                "--smb-flags=--shares",
                "-s",
                "smb",
            ],
            "smb",
            ["--shares"],
            id="only-own-service-flags",
        ),
    ],
)
def test_per_service_flags(cli_args, service, expected_tail):
    cmd = _parse_and_build(cli_args, service)
    for token in expected_tail:
        assert token in cmd, f"{token!r} not found in {cmd}"
    # Verify ldap bloodhound tokens don't leak into smb command
    if "smb" in cli_args and "--ldap-flags" in " ".join(cli_args):
        assert "--bloodhound" not in cmd


# ---------------------------------------------------------------------------
# Global nxc flags passed through to the command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cli_args, service, expected_tail",
    [
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--continue-on-success",
                "-s",
                "smb",
            ],
            "smb",
            ["--continue-on-success"],
            id="continue-on-success",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "--no-bruteforce", "-s", "smb"],
            "smb",
            ["--no-bruteforce"],
            id="no-bruteforce",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "-t", "50", "-s", "smb"],
            "smb",
            ["-t", "50"],
            id="threads",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "--timeout", "10", "-s", "smb"],
            "smb",
            ["--timeout", "10"],
            id="nxc-timeout",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "-k", "-s", "smb"],
            "smb",
            ["-k"],
            id="kerberos",
        ),
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-H",
                "aad3b435b51404eeaad3b435b51404ee:HASH",
                "-s",
                "smb",
            ],
            "smb",
            ["-H", "aad3b435b51404eeaad3b435b51404ee:HASH"],
            id="ntlm-hash",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "--verbose", "-s", "smb"],
            "smb",
            ["--verbose"],
            id="verbose",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "--debug", "-s", "smb"],
            "smb",
            ["--debug"],
            id="debug",
        ),
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "--gfail-limit",
                "3",
                "-s",
                "smb",
            ],
            "smb",
            ["--gfail-limit", "3"],
            id="gfail-limit",
        ),
        pytest.param(
            ["10.0.0.1", "-u", "admin", "-p", "pass", "-M", "mimikatz", "-s", "smb"],
            "smb",
            ["-M", "mimikatz"],
            id="module",
        ),
        pytest.param(
            [
                "10.0.0.1",
                "-u",
                "admin",
                "-p",
                "pass",
                "-M",
                "mimikatz",
                "-o",
                "COMMAND=sekurlsa::logonpasswords",
                "-s",
                "smb",
            ],
            "smb",
            ["-M", "mimikatz", "-o", "COMMAND=sekurlsa::logonpasswords"],
            id="module-with-options",
        ),
    ],
)
def test_global_flags(cli_args, service, expected_tail):
    cmd = _parse_and_build(cli_args, service)
    joined = " ".join(cmd)
    assert " ".join(expected_tail) in joined, (
        f"Expected {expected_tail} in command {cmd}"
    )


# ---------------------------------------------------------------------------
# Service is always the correct protocol in the command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "service",
    ["ldap", "smb", "ssh", "winrm", "mssql", "ftp", "rdp", "vnc", "wmi", "nfs"],
)
def test_service_name_in_command(service):
    cmd = _parse_and_build(["10.0.0.1", "-s", service], service)
    assert cmd[0] == "nxc"
    assert cmd[1] == service
