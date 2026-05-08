#!/usr/bin/env python3
import json
import os
import subprocess
import sys

from nxc.builder import build_command
from nxc.cli import build_arg_parser, extract_global_flags, extract_service_flags
from nxc.config import create_default_config, deep_merge, load_config
from nxc.runner import run_service
from nxc.services import ALL_SERVICES, parse_services

_WIDE = "═" * 64
_THIN = "─" * 64

_SERVICE_SET = set(ALL_SERVICES)


def prog_name() -> str:
    """Name of the program as it was invoked (e.g. "nxc-scan" or "nxc_scan.py")."""
    return os.path.basename(sys.argv[0]) or "nxc-scan"


def print_brief_usage() -> None:
    p = prog_name()
    protos = "  ".join(f"{i + 1}.{s}" for i, s in enumerate(ALL_SERVICES))
    print(f"""
{_WIDE}
  nxc-scan  —  netexec multi-protocol wrapper
{_WIDE}

  Usage:
    {p} <target> [options]
    {p} --config FILE [<target>] [options]

  Examples:
    {p} 10.0.0.1
    {p} 10.0.0.1 -u admin -p pass
    {p} 10.0.0.1 -s smb,ldap -u admin -p pass --continue-on-success
    {p} 10.0.0.1 -s 1-3 --service-timeout 30
    {p} 10.0.0.1 --smb-flags="--shares" --ldap-flags="--bloodhound -c All"
    {p} --config my_config.json 10.0.0.1

  Protocols:
    {protos}

  Help levels:
    -h              flag reference
    -hh             full reference with all flags and examples
    smb -h          nxc's own help for the smb protocol  (any protocol name)
    --dump-config   print a config template and exit
{_WIDE}""")


def print_extended_help() -> None:
    p = prog_name()
    protos_grid = "\n    ".join(
        "  ".join(f"{i + 1:2d}. {ALL_SERVICES[i]:<6}" for i in row)
        for row in [range(0, 5), range(5, 10)]
    )
    svc_flag_rows = "\n  ".join(f'  --{s}-flags  "FLAGS"' for s in ALL_SERVICES)
    print(f"""
{_WIDE}
  nxc-scan  —  full reference
{_WIDE}

USAGE
  {p} <target> [options]
  {p} --config FILE [<target>] [options]

CORE OPTIONS
  target                     IP, CIDR, hostname, range, or file of targets
  -u / --username  USER|FILE  single username or file of usernames
  -p / --password  PASS|FILE  single password or file of passwords
  -s / --services  SELECTION  protocols to run  (default: all — see SERVICE SELECTION)
  --service-timeout  SECONDS  kill each nxc process after N seconds and move on
  --config  FILE              load defaults from a JSON config file
  --dump-config               print a config template to stdout and exit

SERVICE SELECTION  (-s / --services)
  Comma-separated tokens, freely mixed:

    all  /  *          every protocol
    1-3                inclusive range by 1-based index  →  ldap, wmi, mssql
    1,3,5              explicit indices
    smb,ldap           by name
    -2                 exclude index 2 from the full set  (note: use -s=-2 on CLI)
    -smb               exclude by name  (use -s=-smb)
    mixing both        e.g. 1-5,-3  →  protocols 1-5 except #3

  Protocols:
    {protos_grid}

OUTPUT
  --verbose              verbose nxc output
  --debug                debug-level nxc output
  --no-progress          disable the nxc progress bar
  --log  FILE            append nxc output to FILE

THREADING / TIMING
  -t / --threads  N      concurrent threads  (nxc default: 256)
  --timeout  SECONDS     nxc per-thread connection timeout  (not the process timeout)
  --jitter  INTERVAL     random delay between authentications  (e.g. "0-2")

DNS
  -6                     force IPv6
  --dns-server  IP       custom DNS server  (default: system DNS)
  --dns-tcp              use TCP for DNS queries
  --dns-timeout  SECONDS DNS query timeout in seconds

AUTHENTICATION
  -H / --hash  HASH|FILE NTLM hash(es) or file of hashes
  -id / --cred-id  ID    database credential ID
  --no-bruteforce        skip spray mode when using username/password files
  --continue-on-success  keep spraying after a valid credential is found
  --ignore-pw-decoding   ignore non-UTF-8 bytes in password file
  --gfail-limit  N       stop after N global failed logins
  --ufail-limit  N       stop after N failed logins for a single username
  --fail-limit   N       stop after N failed logins against a single host

KERBEROS
  -k / --kerberos        use Kerberos authentication
  --use-kcache           use the local Kerberos ticket cache
  --aesKey  KEY          AES key(s) for Kerberos authentication
  --kdcHost  HOST        KDC hostname / IP

CERTIFICATES
  --pfx-cert   FILE      PFX/PKCS12 certificate file
  --pfx-base64 B64       PFX certificate as a base64-encoded string
  --pfx-pass   PASS      PFX passphrase
  --pem-cert   FILE      PEM certificate file
  --pem-key    FILE      PEM private key file

MODULES  (applied to every selected protocol)
  -M / --module  MODULE  nxc module to load
  -o / --module-options  K=V   module option(s)

PER-PROTOCOL FLAGS
  Append extra flags only for one specific protocol's invocation:

  {svc_flag_rows}

  Examples:
    --smb-flags="--share C$ --spider --regex \\.txt$"
    --ldap-flags="--bloodhound -c All"
    --ssh-flags="-x 'id && hostname'"
    --mssql-flags="-q 'SELECT @@version'"
    --wmi-flags="--wmi-query 'SELECT * FROM Win32_Process'"

CONFIG FILE
  Generate a template, edit it, then pass it with --config:

    {p} --dump-config > my_config.json

  Top-level keys in the JSON:
    target, username, password, services, service_timeout
    global_flags   (dict — one key per flag in the sections above)
    service_flags  (dict — one key per protocol, value is a flags string)

  CLI flags always override config file values.

HELP LEVELS
  (no args)       this quick-start banner
  -h              flag reference  (all flags with short descriptions)
  -hh             this page
  smb -h          nxc's own help for the smb protocol  (any protocol name)
  --dump-config   print a config template and exit

EXAMPLES
  # Unauthenticated sweep of all protocols
  {p} 10.0.0.1

  # Credential spray — keep going after first hit
  {p} 10.0.0.1 -u users.txt -p passwords.txt --continue-on-success

  # SMB + LDAP only, kill each scan after 60 s
  {p} 10.0.0.1 -s smb,ldap -u admin -p pass --service-timeout 60

  # Protocols 1-3 with Kerberos
  {p} dc.corp.local -s 1-3 -u admin -k

  # SMB spider + LDAP bloodhound in one run
  {p} 10.0.0.1 -u admin -p pass \\
      --smb-flags="--share C$ --spider --regex \\.txt$" \\
      --ldap-flags="--bloodhound -c All"

  # Load config, override target on CLI
  {p} --config engagements/corp.json 10.0.0.1

  # Exclude SMB, 45-second per-service timeout
  {p} 10.0.0.1 -s=-smb --service-timeout 45

  # Hash-based auth, NTLM only
  {p} 10.0.0.1 -u admin -H aad3b435b51404eeaad3b435b51404ee:HASH

{_WIDE}""")


def _cred_display(value: str | None) -> str:
    if value is None:
        return "(none)"
    if value == "":
        return "(empty)"
    return value


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
    if not raw:
        print_brief_usage()
        sys.exit(0)

    if "-hh" in raw:
        print_extended_help()
        sys.exit(0)

    # "<proto> -h" → delegate to nxc's own protocol help
    first = raw[0]
    if first in _SERVICE_SET and ("-h" in raw or "--help" in raw):
        subprocess.run(["nxc", first, "--help"])
        sys.exit(0)

    parser = build_arg_parser()
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
    ]:
        if (val := getattr(args, attr)) is not None:
            cfg[key] = val

    for k, v in extract_global_flags(args).items():
        if v is not None:
            cfg["global_flags"][k] = v

    for svc, flags in extract_service_flags(args).items():
        if flags is not None:
            cfg["service_flags"][svc] = flags

    services = parse_services(cfg.get("services") or "all")
    if not services:
        print("[!] No protocols matched the selection — nothing to run.")
        sys.exit(1)

    service_timeout: int | None = cfg.get("service_timeout")
    target = cfg.get("target") or ""

    print_header(
        target,
        cfg.get("username"),
        cfg.get("password"),
        services,
        service_timeout,
    )

    results: dict[str, int] = {}
    for service in services:
        cmd = build_command(service, cfg)
        results[service] = run_service(service, cmd, service_timeout)

    print_summary(results)


if __name__ == "__main__":
    main()
