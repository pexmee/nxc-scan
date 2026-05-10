import argparse
from typing import Any

from rich.console import Console
from rich.rule import Rule
from rich_argparse import RawDescriptionRichHelpFormatter

from .services import ALL_SERVICES

# Shared console — force colour even when stdout is not a tty (e.g. piped).
# Set to False if you want colour stripped when redirected.
_console = Console(highlight=False)


# ---------------------------------------------------------------------------
# Extended help (-hh)
# ---------------------------------------------------------------------------


def _print_extra_sections(console: Console, prog: str) -> None:
    """Print the extended reference sections (service selection, examples, config)."""

    def rule(title: str) -> None:
        console.print(Rule(f"[bold cyan]{title}[/]", style="dim"))

    def h(text: str) -> None:
        console.print(f"  [bold white]{text}[/]")

    rule("service selection detail")
    console.print()
    h("Tokens are comma-separated and freely mixed:")
    console.print()
    rows = [
        ("[bold yellow]all[/], [bold yellow]*[/]", "every protocol (default)"),
        ("[bold yellow]1-3[/]", "range by 1-based index  (ldap, wmi, mssql)"),
        ("[bold yellow]1,3,5[/]", "explicit indices"),
        ("[bold yellow]smb,ldap[/]", "explicit names"),
        ("[bold yellow]-s=-2[/]", "exclude index 2  (use = to avoid dash ambiguity)"),
        ("[bold yellow]-s=-smb[/]", "exclude by name"),
        ("[bold yellow]-s=1-5,-3[/]", "range with exclusion"),
    ]
    for flag, desc in rows:
        console.print(f"    {flag:<40}[dim]{desc}[/]")

    console.print()
    h("Protocols:")
    console.print()
    for row in [range(0, 5), range(5, 10)]:
        line = "  ".join(
            f"  [cyan]{i + 1:2d}.[/] [bold]{ALL_SERVICES[i]:<6}[/]" for i in row
        )
        console.print(f"    {line}")

    console.print()
    rule("per-protocol flags")
    console.print()
    for svc in ALL_SERVICES:
        console.print(f'    [bold yellow]--{svc}-flags[/] [dim]"FLAGS"[/]')
    console.print()
    h("Examples:")
    for ex in [
        '--smb-flags="--share C$ --spider C$ --regex \\.txt$"',
        '--ldap-flags="--bloodhound -c All"',
        "--ssh-flags=\"-x 'id && hostname'\"",
        "--mssql-flags=\"-q 'SELECT @@version'\"",
        "--wmi-flags=\"--wmi-query 'SELECT * FROM Win32_Process'\"",
    ]:
        console.print(f"    [green]{ex}[/]")

    console.print()
    rule("examples")
    console.print()
    examples = [
        ("unauthenticated sweep of all protocols", f"{prog} 10.0.0.1"),
        (
            "credential spray — keep going after first hit",
            f"{prog} 10.0.0.1 -u users.txt -p passwords.txt --continue-on-success",
        ),
        (
            "smb + ldap only, kill each scan after 60 s",
            f"{prog} 10.0.0.1 -s smb,ldap -u admin -p pass --service-timeout 60",
        ),
        ("protocols 1-3 with kerberos", f"{prog} dc.corp.local -s 1-3 -u admin -k"),
        (
            "smb spider + ldap bloodhound in one run",
            f"{prog} 10.0.0.1 -u admin -p pass \\\n"
            f'    --smb-flags="--share C$ --spider C$ --regex \\.txt$" \\\n'
            f'    --ldap-flags="--bloodhound -c All"',
        ),
        ("load config, override target on CLI", f"{prog} --config corp.json 10.0.0.1"),
        (
            "exclude smb, 45-second per-service timeout",
            f"{prog} 10.0.0.1 -s=-smb --service-timeout 45",
        ),
        (
            "hash-based auth",
            f"{prog} 10.0.0.1 -u admin -H aad3b435b51404eeaad3b435b51404ee:HASH",
        ),
        (
            "null-session (explicit empty credentials)",
            f"{prog} 10.0.0.1 -u '' -p '' -s smb",
        ),
    ]
    for comment, cmd in examples:
        console.print(f"  [dim]# {comment}[/]")
        console.print(f"  [green]{cmd}[/]")
        console.print()

    rule("config file")
    console.print()
    console.print(
        "  Generate a template, edit it, then pass with [bold yellow]--config[/]:"
    )
    console.print()
    console.print(f"    [green]{prog} --dump-config > my_config.json[/]")
    console.print()
    h("Top-level JSON keys:")
    console.print()
    for key, desc in [
        ("target, username, password, services, service_timeout", "core options"),
        ("global_flags", "dict — one key per global flag (snake_case)"),
        ("service_flags", "dict — one key per protocol; value is a flags string"),
    ]:
        console.print(f"    [bold yellow]{key}[/]  [dim]{desc}[/]")
    console.print()
    console.print("  [dim]CLI flags always override config file values.[/]")
    console.print()


class ExtendedHelpAction(argparse.Action):
    """Implements -hh: standard argparse help + full reference manual via Rich."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: str = argparse.SUPPRESS,
        help: str | None = None,
    ) -> None:
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        parser.print_help()
        _print_extra_sections(_console, parser.prog)
        parser.exit()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _service_selection_epilog() -> str:
    """Epilog text shown at the bottom of -h.  Supports Rich markup."""
    proto_list = "  ".join(
        f"[cyan]{i + 1}.[/][bold]{s}[/]" for i, s in enumerate(ALL_SERVICES)
    )
    return (
        "[bold]service selection[/]  [dim](-s / --services)[/dim]:\n"
        "  [yellow]all[/], [yellow]*[/]       every protocol (default)\n"
        "  [yellow]1-3[/]          range by index: ldap, wmi, mssql\n"
        "  [yellow]1,3,5[/]        explicit indices\n"
        "  [yellow]smb,ldap[/]     by name\n"
        "  [yellow]-s=-smb[/]      exclude by name  (use = to avoid dash ambiguity)\n"
        "  [yellow]-s=1-5,-3[/]    range with exclusion\n"
        "\n"
        "[bold]protocols[/]:\n"
        f"  {proto_list}\n"
        "\n"
        "run [bold cyan]-hh[/] for the full manual, or [bold cyan]<proto> -h[/] for nxc's own help\n"
        "[dim](e.g. nxc-scan smb -h)[/]"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nxc-scan",
        description=(
            "[bold]netexec[/] (nxc) multi-protocol wrapper — "
            "scan all or selected protocols in one command."
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
        epilog=_service_selection_epilog(),
    )

    # ── Extended help ──────────────────────────────────────────────────────
    p.add_argument(
        "-hh",
        action=ExtendedHelpAction,
        help="Show the full reference manual (flag details, examples, config format)",
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
        help='Protocols to run — "all", range (1-3), list (smb,ldap), or exclusion (-s=-smb). Default: all.',
    )
    p.add_argument(
        "--service-timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Kill each protocol process after N seconds and move on (independent of --timeout)",
    )
    p.add_argument(
        "--config",
        default=None,
        metavar="FILE",
        help="JSON config file — CLI flags override any config values",
    )
    p.add_argument(
        "--dump-config",
        action="store_true",
        help="Print a template JSON config to stdout and exit",
    )
    p.add_argument(
        "--output-file",
        default=None,
        metavar="FILE",
        help="Tee output to FILE while still printing to the console",
    )

    # ── Global nxc flags ──────────────────────────────────────────────────
    g = p.add_argument_group("global nxc flags", "Forwarded to every protocol run.")

    g.add_argument(
        "-t",
        "--threads",
        type=int,
        default=None,
        metavar="N",
        help="Concurrent threads (nxc default: 256)",
    )
    g.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Per-thread connection timeout",
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
        "--log", default=None, metavar="FILE", help="Append nxc output to FILE"
    )
    g.add_argument(
        "--verbose",
        action="store_const",
        const=True,
        default=None,
        help="Verbose output",
    )
    g.add_argument(
        "--debug", action="store_const", const=True, default=None, help="Debug output"
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
        help="DNS server (default: system DNS)",
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
        help="DNS query timeout",
    )
    g.add_argument(
        "-H",
        "--hash",
        default=None,
        metavar="HASH_OR_FILE",
        help="NTLM hash(es) or file of hashes",
    )
    g.add_argument(
        "-id",
        "--cred-id",
        dest="cred_id",
        default=None,
        metavar="ID",
        help="Database credential ID",
    )
    g.add_argument(
        "--ignore-pw-decoding",
        dest="ignore_pw_decoding",
        action="store_const",
        const=True,
        default=None,
        help="Ignore non-UTF-8 bytes in password file",
    )
    g.add_argument(
        "--no-bruteforce",
        dest="no_bruteforce",
        action="store_const",
        const=True,
        default=None,
        help="No spray when using username/password files",
    )
    g.add_argument(
        "--continue-on-success",
        dest="continue_on_success",
        action="store_const",
        const=True,
        default=None,
        help="Keep spraying after a valid credential is found",
    )
    g.add_argument(
        "--gfail-limit",
        dest="gfail_limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N global failed logins",
    )
    g.add_argument(
        "--ufail-limit",
        dest="ufail_limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N failures for a single username",
    )
    g.add_argument(
        "--fail-limit",
        dest="fail_limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N failures against a single host",
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
        help="AES key(s) for Kerberos",
    )
    g.add_argument(
        "--kdcHost",
        dest="kdc_host",
        default=None,
        metavar="HOST",
        help="KDC hostname / IP",
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
        help="PFX certificate as base64 string",
    )
    g.add_argument(
        "--pfx-pass",
        dest="pfx_pass",
        default=None,
        metavar="PASS",
        help="PFX passphrase",
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
        help="Module options for -M",
    )

    # ── Per-service flags ─────────────────────────────────────────────────
    sv = p.add_argument_group(
        "per-protocol flags",
        'Appended only to that protocol\'s invocation.  e.g. [green]--smb-flags="--shares"[/]',
    )
    for svc in ALL_SERVICES:
        sv.add_argument(
            f"--{svc}-flags",
            dest=f"{svc}_flags",
            default=None,
            metavar="FLAGS",
            help=f"Extra flags for {svc}",
        )

    # ── Per-service batches ───────────────────────────────────────────────
    sb = p.add_argument_group(
        "per-protocol batches",
        "Run a protocol multiple times with different flag sets.",
    )
    for svc in ALL_SERVICES:
        sb.add_argument(
            f"--batch-{svc}",
            dest=f"batch_{svc}",
            nargs="?",
            const=True,
            default=None,
            metavar="JSON",
            help=f"Batch runs for {svc} — optionally supply an inline JSON list of flag lists",
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


def extract_service_batches(args: argparse.Namespace) -> dict[str, str | bool | None]:
    """Return per-service batches from *args* (``None`` = unset, ``True`` = use config)."""
    return {svc: getattr(args, f"batch_{svc}") for svc in ALL_SERVICES}
