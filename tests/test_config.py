"""Tests for nxc/config.py and the full --config file pipeline.

NamedTemporaryFile is used throughout so tests never touch permanent paths.
"""

import json
import os
import tempfile

import pytest

from nxc.builder import build_command
from nxc.cli import build_arg_parser, extract_global_flags, extract_service_flags
from nxc.config import create_default_config, deep_merge, load_config
from nxc.services import ALL_SERVICES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmp_config(data: dict) -> str:
    """Write *data* to a NamedTemporaryFile and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, f)
    f.close()
    return f.name


def _parse_and_build(cli_args: list[str], service: str) -> list[str]:
    """Simulate main()'s full config pipeline for a single service."""
    parser = build_arg_parser()
    args = parser.parse_args(cli_args)
    cfg = create_default_config()

    if args.config:
        cfg = deep_merge(cfg, load_config(args.config))

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
# create_default_config
# ---------------------------------------------------------------------------


def test_default_config_top_level_keys():
    cfg = create_default_config()
    for key in (
        "target",
        "username",
        "password",
        "services",
        "service_timeout",
        "output_file",
        "global_flags",
        "service_flags",
        "service_batches",
    ):
        assert key in cfg, f"missing key: {key}"


def test_default_config_services_all():
    assert create_default_config()["services"] == "all"


def test_default_config_credentials_none():
    cfg = create_default_config()
    assert cfg["username"] is None
    assert cfg["password"] is None


def test_default_config_service_flags_all_protocols():
    cfg = create_default_config()
    for svc in ALL_SERVICES:
        assert svc in cfg["service_flags"]


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_reads_file():
    data = {"target": "10.0.0.1", "username": "admin", "password": "pass"}
    path = _tmp_config(data)
    try:
        result = load_config(path)
        assert result == data
    finally:
        os.unlink(path)


def test_load_config_integer_values():
    data = {"service_timeout": 30, "global_flags": {"threads": 50}}
    path = _tmp_config(data)
    try:
        result = load_config(path)
        assert result["service_timeout"] == 30
        assert result["global_flags"]["threads"] == 50
    finally:
        os.unlink(path)


def test_load_config_null_values():
    data = {"target": None, "service_timeout": None}
    path = _tmp_config(data)
    try:
        result = load_config(path)
        assert result["target"] is None
        assert result["service_timeout"] is None
    finally:
        os.unlink(path)


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/tmp/this_does_not_exist_nxc_scan_test.json")


def test_load_config_invalid_json():
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    f.write("{ not valid json }")
    f.close()
    try:
        with pytest.raises(json.JSONDecodeError):
            load_config(f.name)
    finally:
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------


def test_deep_merge_override_scalar():
    base = {"target": None, "username": None}
    override = {"target": "10.0.0.1"}
    result = deep_merge(base, override)
    assert result["target"] == "10.0.0.1"
    assert result["username"] is None  # untouched


def test_deep_merge_none_in_override_skipped():
    base = {"target": "10.0.0.1"}
    override = {"target": None}
    result = deep_merge(base, override)
    assert result["target"] == "10.0.0.1"  # None does not clobber


def test_deep_merge_nested_dict():
    base = {"global_flags": {"threads": None, "verbose": False}}
    override = {"global_flags": {"threads": 50}}
    result = deep_merge(base, override)
    assert result["global_flags"]["threads"] == 50
    assert result["global_flags"]["verbose"] is False  # untouched


def test_deep_merge_nested_none_skipped():
    base = {"global_flags": {"threads": 10}}
    override = {"global_flags": {"threads": None}}
    result = deep_merge(base, override)
    assert result["global_flags"]["threads"] == 10


def test_deep_merge_does_not_mutate_base():
    base = {"target": "10.0.0.1"}
    override = {"target": "192.168.1.1"}
    deep_merge(base, override)
    assert base["target"] == "10.0.0.1"


def test_deep_merge_new_key_added():
    base = {"a": 1}
    override = {"b": 2}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# Full --config pipeline → build_command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config_data, service, expected_cmd",
    [
        pytest.param(
            {"target": "10.0.0.1", "username": "admin", "password": "pass"},
            "smb",
            ["nxc", "smb", "10.0.0.1", "-u", "admin", "-p", "pass"],
            id="target-and-creds-from-config",
        ),
        pytest.param(
            {"target": "10.0.0.1"},
            "ldap",
            ["nxc", "ldap", "10.0.0.1"],
            id="target-only-from-config",
        ),
        pytest.param(
            {"target": "10.0.0.1", "username": "", "password": ""},
            "smb",
            ["nxc", "smb", "10.0.0.1", "-u", "", "-p", ""],
            id="empty-string-creds-from-config",
        ),
        pytest.param(
            {"target": "10.0.0.1", "global_flags": {"continue_on_success": True}},
            "smb",
            ["nxc", "smb", "10.0.0.1", "--continue-on-success"],
            id="global-flag-from-config",
        ),
        pytest.param(
            {"target": "10.0.0.1", "global_flags": {"threads": 50}},
            "smb",
            ["nxc", "smb", "10.0.0.1", "-t", "50"],
            id="threads-from-config",
        ),
        pytest.param(
            {
                "target": "10.0.0.1",
                "service_flags": {"smb": "--shares", "ldap": "--bloodhound -c All"},
            },
            "smb",
            ["nxc", "smb", "10.0.0.1", "--shares"],
            id="smb-service-flags-from-config",
        ),
        pytest.param(
            {
                "target": "10.0.0.1",
                "service_flags": {"smb": "--shares", "ldap": "--bloodhound -c All"},
            },
            "ldap",
            ["nxc", "ldap", "10.0.0.1", "--bloodhound", "-c", "All"],
            id="ldap-service-flags-from-config",
        ),
    ],
)
def test_config_file_pipeline(config_data, service, expected_cmd):
    path = _tmp_config(config_data)
    try:
        cmd = _parse_and_build(["--config", path], service)
        assert cmd == expected_cmd
    finally:
        os.unlink(path)


def test_cli_overrides_config_file_target():
    """A target on the CLI must win over the target in the config file."""
    path = _tmp_config(
        {"target": "192.168.1.1", "username": "admin", "password": "pass"}
    )
    try:
        cmd = _parse_and_build(["10.0.0.1", "--config", path, "-s", "smb"], "smb")
        assert "10.0.0.1" in cmd
        assert "192.168.1.1" not in cmd
    finally:
        os.unlink(path)


def test_cli_overrides_config_file_credentials():
    """CLI credentials must win over config-file credentials."""
    path = _tmp_config(
        {"target": "10.0.0.1", "username": "config_user", "password": "config_pass"}
    )
    try:
        cmd = _parse_and_build(
            [
                "10.0.0.1",
                "--config",
                path,
                "-u",
                "cli_user",
                "-p",
                "cli_pass",
                "-s",
                "smb",
            ],
            "smb",
        )
        assert "-u" in cmd
        assert cmd[cmd.index("-u") + 1] == "cli_user"
        assert cmd[cmd.index("-p") + 1] == "cli_pass"
    finally:
        os.unlink(path)


def test_service_timeout_from_config_is_integer():
    """service_timeout loaded from JSON must be an int so subprocess.run accepts it."""
    path = _tmp_config({"service_timeout": 5})
    try:
        cfg = create_default_config()
        cfg = deep_merge(cfg, load_config(path))
        timeout = cfg.get("service_timeout")
        assert isinstance(timeout, int)
        assert timeout == 5
    finally:
        os.unlink(path)


def test_config_null_service_timeout_stays_none():
    """service_timeout: null in JSON must not override the default None."""
    path = _tmp_config({"service_timeout": None})
    try:
        cfg = create_default_config()
        cfg = deep_merge(cfg, load_config(path))
        assert cfg.get("service_timeout") is None
    finally:
        os.unlink(path)
