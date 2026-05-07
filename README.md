# nxc-scan

A thin Python wrapper around [netexec](https://www.netexec.wiki/) (`nxc`) that
runs the same target/credential pair across many `nxc` protocols in a single
command, with per-protocol flags, a per-service process timeout, and an
optional JSON config file.

## What it does

`nxc-scan` calls the underlying `nxc` binary once per selected protocol.
For each protocol it builds an `nxc <protocol> <target> [auth] [flags]`
invocation, runs it as a subprocess, optionally enforces a wall-clock timeout,
and prints a summary at the end.

Features:

- One command, many protocols. Pick `all`, a range (`1-3`), an explicit list
  (`smb,ldap`), or an exclusion (`-smb`).
- Optional target, username, and password — each can be a literal value, a
  file path (handed straight to `nxc`), or omitted entirely for unauthenticated
  scans.
- Global flags (e.g. `--continue-on-success`, `--threads`, `--jitter`,
  Kerberos, certificates, modules) are forwarded to every protocol run.
- Per-protocol extra flags: `--smb-flags`, `--ldap-flags`, `--ssh-flags`, etc.
  Each protocol's string is passed through `shlex.split` and appended only to
  that protocol's invocation.
- A `--service-timeout` that kills the current `nxc` process after N seconds
  and moves on to the next protocol. Independent of `nxc`'s own per-thread
  `--timeout`.
- JSON config files via `--config`. Defaults from the file; CLI flags always
  win on top.
- Three help tiers: brief banner (no args), standard reference (`-h`), full
  manual (`-hh`), plus delegation to `nxc`'s native help (`smb -h`,
  `ldap -h`, ...).

## Requirements

- Python 3.12 or newer.
- The `nxc` binary on your `PATH`. Install netexec from
  https://www.netexec.wiki/ or via `pipx install netexec`.
- [uv](https://docs.astral.sh/uv/) (recommended) for running the project.

## Install with uv

```bash
git clone https://github.com/pexmee/nxc-scan.git
cd nxc-scan
uv sync
```

The project has zero runtime dependencies, so `uv sync` only sets up the
Python interpreter and a virtualenv.

## Run

With uv:

```bash
uv run python nxc_scan.py <args>
```

Or, after activating the venv (`source .venv/bin/activate`), simply:

```bash
python nxc_scan.py <args>
```

If you want a shorter command, you can mark the script executable and call
it directly:

```bash
chmod +x nxc_scan.py
./nxc_scan.py <args>
```

## Usage examples

Quick-start banner (printed when run with no arguments):

```bash
uv run python nxc_scan.py
```

Unauthenticated sweep of every protocol:

```bash
uv run python nxc_scan.py 10.0.0.1
```

Credential spray, keep going after the first valid hit:

```bash
uv run python nxc_scan.py 10.0.0.1 -u users.txt -p passwords.txt --continue-on-success
```

SMB and LDAP only, kill each scan after 60 seconds:

```bash
uv run python nxc_scan.py 10.0.0.1 -s smb,ldap -u admin -p pass --service-timeout 60
```

Protocols 1 through 3 with Kerberos:

```bash
uv run python nxc_scan.py dc.corp.local -s 1-3 -u admin -k
```

SMB share spider plus LDAP BloodHound collection in one run:

```bash
uv run python nxc_scan.py 10.0.0.1 -u admin -p pass \
    --smb-flags="--share C\$ --spider --regex \\.txt$" \
    --ldap-flags="--bloodhound -c All"
```

Exclude a single protocol (use `=` to avoid argparse interpreting the leading
dash as a new option):

```bash
uv run python nxc_scan.py 10.0.0.1 -s=-smb --service-timeout 45
```

Hash-based authentication:

```bash
uv run python nxc_scan.py 10.0.0.1 -u admin -H aad3b435b51404eeaad3b435b51404ee:HASH
```

## Service selection syntax

Pass to `-s` / `--services`. Comma-separated tokens, freely mixed.

| Token         | Meaning                                                    |
|---------------|------------------------------------------------------------|
| `all` / `*`   | Every protocol (default if `-s` is not given)              |
| `1-3`         | Inclusive range by 1-based index (`ldap, wmi, mssql`)      |
| `1,3,5`       | Explicit indices                                           |
| `smb,ldap`    | Explicit names                                             |
| `-2`          | Exclude index 2 (use `-s=-2` on the CLI)                   |
| `-smb`        | Exclude by name (use `-s=-smb`)                            |
| `1-5,-3`      | Mix: range plus exclusion                                  |

Protocol indices:

| #  | Protocol | #  | Protocol |
|----|----------|----|----------|
|  1 | ldap     |  6 | vnc      |
|  2 | wmi      |  7 | winrm    |
|  3 | mssql    |  8 | ssh      |
|  4 | ftp      |  9 | nfs      |
|  5 | rdp      | 10 | smb      |

## Per-protocol flags

Each protocol has a corresponding `--<proto>-flags` option whose value is a
single string. The string is split with `shlex.split`, so quoting works the
same as in the shell:

```bash
--smb-flags="--share C$ --spider --regex \\.txt$"
--ldap-flags="--bloodhound -c All"
--ssh-flags="-x 'id && hostname'"
--mssql-flags="-q 'SELECT @@version'"
--wmi-flags="--wmi-query 'SELECT * FROM Win32_Process'"
```

To see the full list of flags a protocol accepts, delegate to `nxc`'s own
help:

```bash
uv run python nxc_scan.py smb -h
uv run python nxc_scan.py ldap -h
```

## Config file

Generate a template, edit it, then load it with `--config`:

```bash
uv run python nxc_scan.py --dump-config > my_config.json
# edit my_config.json
uv run python nxc_scan.py --config my_config.json 10.0.0.1
```

Top-level JSON keys:

- `target`, `username`, `password`, `services`, `service_timeout`
- `global_flags` — one key per global `nxc` flag (snake_case)
- `service_flags` — one key per protocol; the value is a flags string

CLI flags always override the corresponding values from the config file.

## Help levels

| Invocation                | Output                                                 |
|---------------------------|--------------------------------------------------------|
| `nxc_scan.py`             | Quick-start banner with usage and examples             |
| `nxc_scan.py -h`          | Standard `argparse` flag reference                     |
| `nxc_scan.py -hh`         | Full manual: every option grouped by topic, examples   |
| `nxc_scan.py <proto> -h`  | `nxc`'s native help for that protocol (e.g. `smb -h`)  |
| `nxc_scan.py --dump-config` | Print a config template and exit                     |

## Project layout

```
nxc-scan/
├── nxc_scan.py          Entry point and main() orchestrator
├── nxc_scan_config.json Default config template
├── nxc/                 Helper modules
│   ├── services.py      Protocol list + selection parsing
│   ├── config.py        Config schema, JSON load, deep merge
│   ├── builder.py       Translates a config dict into an nxc argv list
│   ├── runner.py        Subprocess invocation with timeout handling
│   └── cli.py           argparse setup + CLI-to-config bridge
├── pyproject.toml
└── README.md
```

## License

See `LICENSE`.
