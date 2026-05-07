ALL_SERVICES: list[str] = [
    "ldap",
    "wmi",
    "mssql",
    "ftp",
    "rdp",
    "vnc",
    "winrm",
    "ssh",
    "nfs",
    "smb",
]

_SERVICE_INDEX: dict[str, int] = {svc: i for i, svc in enumerate(ALL_SERVICES)}


def parse_services(selection: str) -> list[str]:
    """Resolve a service-selection string to an ordered list of service names."""
    if not selection or selection.strip().lower() in ("all", "*"):
        return list(ALL_SERVICES)

    parts = [p.strip() for p in selection.split(",") if p.strip()]
    include: set[int] = set()
    exclude: set[int] = set()

    for part in parts:
        if part.startswith("-"):
            token = part[1:]
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(ALL_SERVICES):
                    exclude.add(idx)
            elif token.lower() in _SERVICE_INDEX:
                exclude.add(_SERVICE_INDEX[token.lower()])
        elif "-" in part:
            # Range like "1-3"
            lo_str, hi_str = part.split("-", 1)
            if lo_str.isdigit() and hi_str.isdigit():
                for i in range(int(lo_str) - 1, int(hi_str)):
                    if 0 <= i < len(ALL_SERVICES):
                        include.add(i)
        elif part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(ALL_SERVICES):
                include.add(idx)
        elif part.lower() in _SERVICE_INDEX:
            include.add(_SERVICE_INDEX[part.lower()])

    if include:
        selected = include - exclude
    else:
        selected = set(range(len(ALL_SERVICES))) - exclude

    return [ALL_SERVICES[i] for i in sorted(selected)]
