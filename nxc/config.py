import json
from typing import Any

from .services import ALL_SERVICES


def create_default_config() -> dict[str, Any]:
    """Return a fully-populated config dict with all keys set to safe defaults."""
    return {
        "target": None,
        "username": None,
        "password": None,
        "services": "all",
        "service_timeout": None,
        "output_file": None,
        "global_flags": {
            # Generic
            "threads": None,
            "timeout": None,
            "jitter": None,
            "no_progress": False,
            "log": None,
            "verbose": False,
            "debug": False,
            # DNS
            "ipv6": False,
            "dns_server": None,
            "dns_tcp": False,
            "dns_timeout": None,
            # Authentication
            "hash": None,
            "cred_id": None,
            "ignore_pw_decoding": False,
            "no_bruteforce": False,
            "continue_on_success": False,
            "gfail_limit": None,
            "ufail_limit": None,
            "fail_limit": None,
            # Kerberos
            "kerberos": False,
            "use_kcache": False,
            "aes_key": None,
            "kdc_host": None,
            # Certificates
            "pfx_cert": None,
            "pfx_base64": None,
            "pfx_pass": None,
            "pem_cert": None,
            "pem_key": None,
            # Modules
            "module": None,
            "module_options": None,
        },
        "service_flags": {svc: "" for svc in ALL_SERVICES},
    }


def load_config(path: str) -> dict[str, Any]:
    """Load and return a config dict from a JSON file."""
    with open(path) as fh:
        return json.load(fh)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with *override* merged into *base*.

    Nested dicts are merged recursively. ``None`` values in *override* are
    skipped so that missing-or-null JSON fields do not clobber defaults.
    """
    result = base.copy()
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], val)
        elif val is not None:
            result[key] = val
    return result
