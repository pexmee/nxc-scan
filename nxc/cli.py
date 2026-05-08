import argparse
from typing import Any

from .services import ALL_SERVICES


def _protocol_list() -> str:
    return "\n".join(f"  {i + 1:2d}. {svc}" for i, svc in enumerate(ALL_SERVICES))


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nxc-scan",
        description=(
            "netexec (nxc) multi-protocol wrapper.\n"
            "Runs nxc scans across all or a selected subset of protocols."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
protocols (1-{len(ALL_SERVICES)}):
{_protocol_list()}

service selection examples:
  all          run every protocol (default)
  1-3          protocols 1 through 3 (ldap, wmi, mssql)
  1,3,5        protocols 1, 3 and 5
  smb,ldap     by name
  -2           exclude protocol 2, run the rest
  -smb         exclude smb, run the rest
  (exclusions with no includes = full set minus excluded)

per-service flag examples:
  --smb-flags="--share C$ --spider --regex \\.(txt|xml)$"
  --ssh-flags="-x whoami"
  --ldap-flags="--bloodhound -c All"

json config:
  use --config path/to/config.json to load defaults from a file.
  CLI flags always override config values.
  run --dump-config to print a ready-to-edit template and exit.
""",
    )

    # ── Core ──────────────────────────────────────────────────────────────
    p.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Target IP, range, CIDR, hostname, FQDN, or file of targets",
    )
    p.add_argument(
        "-u",
        "--username",
        default=None,
        metavar="USER_OR_FILE",
        help="Username or file containing usernames",
    )
    p.add_argument(
        "-p",
        "--password",
        default=None,
        metavar="PASS_OR_FILE",
        help="Password or file containing passwords",
    )
    p.add_argument(
        "-s",
        "--services",
        default=None,
        metavar="SELECTION",
        help=(
            'Protocols to run. Accepts: "all", a range (1-3), a list (1,2,3 or smb,ldap), '
            "or an exclusion prefix with - (-1 or -smb). Defaults to all."
        ),
    )
    p.add_argument(
        "--service-timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help=(
            "Kill each protocol scan after this many seconds and move on to the next. "
            "Independent of nxc's own --timeout (per-thread limit)."
        ),
    )
    p.add_argument(
        "--config",
        default=None,
        metavar="FILE",
        help="Path to a JSON config file. CLI flags override any config values.",
    )
    p.add_argument(
        "--dump-config",
        action="store_true",
        help="Print a template JSON config to stdout and exit.",
    )
    p.add_argument(
        "--output-file",
        default=None,
        metavar="FILE",
        help="Pipe output to a file as it simultaneously prints to the console",
    )

    # ── Global nxc flags ──────────────────────────────────────────────────
    g = p.add_argument_group("global nxc flags  (applied to every protocol run)")

    g.add_argument(
        "-t",
        "--threads",
        type=int,
        default=None,
        metavar="N",
        help="Number of concurrent threads (nxc default: 256)",
    )
    g.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="nxc per-thread timeout in seconds",
    )
    g.add_argument(
        "--jitter",
        default=None,
        metavar="INTERVAL",
        help="Random delay between authentications (e.g. '0-2')",
    )
    g.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_const",
        const=True,
        default=None,
        help="Disable progress bar",
    )
    g.add_argument(
        "--log", default=None, metavar="FILE", help="Append all output to FILE"
    )
    g.add_argument(
        "--verbose",
        action="store_const",
        const=True,
        default=None,
        help="Enable verbose output",
    )
    g.add_argument(
        "--debug",
        action="store_const",
        const=True,
        default=None,
        help="Enable debug output",
    )
    g.add_argument(
        "-6",
        dest="ipv6",
        action="store_const",
        const=True,
        default=None,
        help="Force IPv6",
    )
    g.add_argument(
        "--dns-server",
        dest="dns_server",
        default=None,
        metavar="IP",
        help="DNS server to use (default: system DNS)",
    )
    g.add_argument(
        "--dns-tcp",
        dest="dns_tcp",
        action="store_const",
        const=True,
        default=None,
        help="Use TCP for DNS queries",
    )
    g.add_argument(
        "--dns-timeout",
        dest="dns_timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="DNS query timeout in seconds",
    )
    g.add_argument(
        "-H",
        "--hash",
        default=None,
        metavar="HASH_OR_FILE",
        help="NTLM hash(es) or file containing NTLM hashes",
    )
    g.add_argument(
        "-id",
        "--cred-id",
        dest="cred_id",
        default=None,
        metavar="ID",
        help="Database credential ID to use for authentication",
    )
    g.add_argument(
        "--ignore-pw-decoding",
        dest="ignore_pw_decoding",
        action="store_const",
        const=True,
        default=None,
        help="Ignore non-UTF-8 characters when decoding the password file",
    )
    g.add_argument(
        "--no-bruteforce",
        dest="no_bruteforce",
        action="store_const",
        const=True,
        default=None,
        help="Disable spray when using username/password files",
    )
    g.add_argument(
        "--continue-on-success",
        dest="continue_on_success",
        action="store_const",
        const=True,
        default=None,
        help="Continue spraying after a valid credential is found",
    )
    g.add_argument(
        "--gfail-limit",
        dest="gfail_limit",
        type=int,
        default=None,
        metavar="N",
        help="Max global failed logins before stopping",
    )
    g.add_argument(
        "--ufail-limit",
        dest="ufail_limit",
        type=int,
        default=None,
        metavar="N",
        help="Max failed logins per username before stopping",
    )
    g.add_argument(
        "--fail-limit",
        dest="fail_limit",
        type=int,
        default=None,
        metavar="N",
        help="Max failed logins per host before stopping",
    )
    g.add_argument(
        "-k",
        "--kerberos",
        action="store_const",
        const=True,
        default=None,
        help="Use Kerberos authentication",
    )
    g.add_argument(
        "--use-kcache",
        dest="use_kcache",
        action="store_const",
        const=True,
        default=None,
        help="Use the local Kerberos ticket cache",
    )
    g.add_argument(
        "--aesKey",
        dest="aes_key",
        default=None,
        metavar="KEY",
        help="AES key(s) to use for Kerberos authentication",
    )
    g.add_argument(
        "--kdcHost",
        dest="kdc_host",
        default=None,
        metavar="HOST",
        help="KDC hostname / IP for Kerberos",
    )
    g.add_argument(
        "--pfx-cert",
        dest="pfx_cert",
        default=None,
        metavar="FILE",
        help="PFX/PKCS12 certificate file",
    )
    g.add_argument(
        "--pfx-base64",
        dest="pfx_base64",
        default=None,
        metavar="B64",
        help="PFX certificate as a base64-encoded string",
    )
    g.add_argument(
        "--pfx-pass",
        dest="pfx_pass",
        default=None,
        metavar="PASS",
        help="Passphrase for the PFX certificate",
    )
    g.add_argument(
        "--pem-cert",
        dest="pem_cert",
        default=None,
        metavar="FILE",
        help="PEM certificate file",
    )
    g.add_argument(
        "--pem-key",
        dest="pem_key",
        default=None,
        metavar="FILE",
        help="PEM private key file",
    )
    g.add_argument(
        "-M",
        "--module",
        dest="module",
        default=None,
        metavar="MODULE",
        help="nxc module to load for every protocol run",
    )
    g.add_argument(
        "-o",
        "--module-options",
        dest="module_options",
        default=None,
        metavar="KEY=VAL",
        help="Module options for -M (passed as-is)",
    )

    # ── Per-service flags ─────────────────────────────────────────────────
    sv = p.add_argument_group(
        "per-protocol extra flags",
        "Extra flags appended only to that protocol's nxc invocation.",
    )
    for svc in ALL_SERVICES:
        sv.add_argument(
            f"--{svc}-flags",
            dest=f"{svc}_flags",
            default=None,
            metavar=f'"{svc.upper()} FLAGS"',
            help=f"Extra flags for the {svc} scan",
        )

    return p


# ---------------------------------------------------------------------------
# CLI → config dict bridge
# ---------------------------------------------------------------------------


def extract_global_flags(args: argparse.Namespace) -> dict[str, Any]:
    """Return a dict of global nxc flag values from *args* (``None`` = unset)."""
    return {
        "threads": args.threads,
        "timeout": args.timeout,
        "jitter": args.jitter,
        "no_progress": args.no_progress,
        "log": args.log,
        "verbose": args.verbose,
        "debug": args.debug,
        "ipv6": args.ipv6,
        "dns_server": args.dns_server,
        "dns_tcp": args.dns_tcp,
        "dns_timeout": args.dns_timeout,
        "hash": args.hash,
        "cred_id": args.cred_id,
        "ignore_pw_decoding": args.ignore_pw_decoding,
        "no_bruteforce": args.no_bruteforce,
        "continue_on_success": args.continue_on_success,
        "gfail_limit": args.gfail_limit,
        "ufail_limit": args.ufail_limit,
        "fail_limit": args.fail_limit,
        "kerberos": args.kerberos,
        "use_kcache": args.use_kcache,
        "aes_key": args.aes_key,
        "kdc_host": args.kdc_host,
        "pfx_cert": args.pfx_cert,
        "pfx_base64": args.pfx_base64,
        "pfx_pass": args.pfx_pass,
        "pem_cert": args.pem_cert,
        "pem_key": args.pem_key,
        "module": args.module,
        "module_options": args.module_options,
    }


def extract_service_flags(args: argparse.Namespace) -> dict[str, str | None]:
    """Return per-service extra flags from *args* (``None`` = unset)."""
    return {svc: getattr(args, f"{svc}_flags") for svc in ALL_SERVICES}
