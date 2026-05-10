#!/usr/bin/env python3
import json
import os
import subprocess
import sys

from nxc.builder import build_command
from nxc.cli import (
    _console,
    build_arg_parser,
    extract_global_flags,
    extract_service_flags,
    extract_service_batches,
)
from nxc.config import create_default_config, deep_merge, load_config
from nxc.runner import run_service
from nxc.services import ALL_SERVICES, parse_services

_WIDE = "═" * 64
_THIN = "─" * 64

_SERVICE_SET = set(ALL_SERVICES)


def prog_name() -> str:
    """Name of the program as it was invoked (e.g. "nxc-scan" or "nxc_scan.py")."""
    return os.path.basename(sys.argv[0]) or "nxc-scan"


def _print_brief_usage() -> None:
    p = prog_name()
    parser = build_arg_parser()
    parser.print_usage(sys.stdout)
    _console.print()
    _console.print("  [bold]quick examples[/bold]")
    _console.print()
    for ex in [
        f"{p} 10.0.0.1",
        f"{p} 10.0.0.1 -u admin -p pass -s smb,ldap",
        f"{p} smb -h",
    ]:
        _console.print(f"    [green]{ex}[/]")
    _console.print()
    _console.print(
        "  [bold cyan]-h[/]  flag reference    "
        "[bold cyan]-hh[/]  full manual    "
        "[bold cyan]--dump-config[/]  config template"
    )
    _console.print()


def _cred_display(value: str | None) -> str:
    if value is None:
        return "(none)"
    if value == "":
        return "(empty)"
    return value


class TeeLogger:
    def __init__(self, filename: str):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")
        self.encoding = getattr(self.terminal, "encoding", "utf-8")
        self.errors = getattr(self.terminal, "errors", "replace")

    def write(self, message: str) -> None:
        try:
            self.terminal.write(message)
        except UnicodeEncodeError:
            safe_msg = message.encode(self.encoding, errors="replace").decode(
                self.encoding
            )
            self.terminal.write(safe_msg)

        self.log.write(message)
        self.terminal.flush()
        self.log.flush()

    def flush(self) -> None:
        self.terminal.flush()
        self.log.flush()

    def isatty(self) -> bool:
        if hasattr(self.terminal, "isatty"):
            return self.terminal.isatty()
        return False

    def fileno(self) -> int:
        if hasattr(self.terminal, "fileno"):
            return self.terminal.fileno()
        raise AttributeError("fileno not available")


def print_header(
    target: str,
    username: str | None,
    password: str | None,
    services: list[str],
    timeout: int | None,
) -> None:
    svc_display = ", ".join(f"{ALL_SERVICES.index(s) + 1}.{s}" for s in services)
    print(f"\n{_WIDE}")
    print("  nxc-scan")
    print(_WIDE)
    print(f"  Target   : {target or '(none)'}")
    print(f"  Username : {_cred_display(username)}")
    print(f"  Password : {_cred_display(password)}")
    print(f"  Services : {svc_display}")
    print(f"  S-Timeout: {f'{timeout}s' if timeout else 'none'}")
    print(_WIDE)


def print_summary(results: dict[str, int]) -> None:
    print(f"\n{_WIDE}")
    print("  Scan summary")
    print(_THIN)
    for svc, rc in results.items():
        if rc == 0:
            status = "OK"
        elif rc == -1:
            status = "TIMEOUT"
        else:
            status = f"FAILED (exit {rc})"
        print(f"  {svc:<8}  {status}")
    print(f"{_WIDE}\n")


def main() -> None:
    raw = sys.argv[1:]

    parser = build_arg_parser()

    # No args → brief usage from argparse + quick-start hint
    if not raw:
        _print_brief_usage()
        sys.exit(0)

    # "<proto> -h" → delegate to nxc's own protocol help
    # Must stay as a pre-parse check because argparse doesn't know nxc protocols
    first = raw[0]
    if first in _SERVICE_SET and ("-h" in raw or "--help" in raw):
        subprocess.run(["nxc", first, "--help"])
        sys.exit(0)
    args = parser.parse_args()

    if args.dump_config:
        print(json.dumps(create_default_config(), indent=2))
        sys.exit(0)

    cfg = create_default_config()

    if args.config:
        cfg = deep_merge(cfg, load_config(args.config))

    for attr, key in [
        ("target", "target"),
        ("username", "username"),
        ("password", "password"),
        ("services", "services"),
        ("service_timeout", "service_timeout"),
        ("output_file", "output_file"),
    ]:
        if (val := getattr(args, attr)) is not None:
            cfg[key] = val

    for k, v in extract_global_flags(args).items():
        if v is not None:
            cfg["global_flags"][k] = v

    for svc, flags in extract_service_flags(args).items():
        if flags is not None:
            cfg["service_flags"][svc] = flags

    for svc, batches in extract_service_batches(args).items():
        if batches is not None:
            if isinstance(batches, str):
                try:
                    cfg["service_batches"][svc] = json.loads(batches)
                except json.JSONDecodeError as e:
                    print(f"[!] Error parsing batch JSON for {svc}: {e}")
                    sys.exit(1)

    services = parse_services(cfg.get("services") or "all")
    if not services:
        print("[!] No protocols matched the selection — nothing to run.")
        sys.exit(1)

    service_timeout: int | None = cfg.get("service_timeout")
    target = cfg.get("target") or ""
    output_file = cfg.get("output_file")

    if output_file:
        sys.stdout = TeeLogger(output_file)

    print_header(
        target,
        cfg.get("username"),
        cfg.get("password"),
        services,
        service_timeout,
    )

    results: dict[str, int] = {}
    for service in services:
        batches = cfg.get("service_batches", {}).get(service)
        if not batches:
            cmd = build_command(service, cfg)
            results[service] = run_service(
                service, cmd, service_timeout, stream_output=bool(output_file)
            )
        else:
            batch_results = []
            for i, batch_flags in enumerate(batches):
                print(
                    f"\n{_THIN}\n  Running {service} batch {i + 1}/{len(batches)}\n{_THIN}"
                )
                flags_str = (
                    " ".join(batch_flags)
                    if isinstance(batch_flags, list)
                    else batch_flags
                )
                batch_cfg = deep_merge(cfg, {"service_flags": {service: flags_str}})
                cmd = build_command(service, batch_cfg)
                rc = run_service(
                    service, cmd, service_timeout, stream_output=bool(output_file)
                )
                batch_results.append(rc)

            if -1 in batch_results:
                results[service] = -1
            else:
                results[service] = next((rc for rc in batch_results if rc != 0), 0)

    print_summary(results)


if __name__ == "__main__":
    main()
