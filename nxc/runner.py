import subprocess
import sys

_SEP = "─" * 64


def run_service(service: str, cmd: list[str], timeout: int | None) -> int:
    """Invoke nxc for *service* and return its exit code.

    Returns ``-1`` when the process is killed by *timeout*. Exits the whole
    program on ``KeyboardInterrupt`` or if the ``nxc`` binary is not found.
    """
    print(f"\n{_SEP}")
    print(f"  Protocol : {service.upper()}")
    print(f"  Command  : {' '.join(cmd)}")
    if timeout:
        print(f"  Timeout  : {timeout}s")
    print(_SEP)

    try:
        result = subprocess.run(cmd, timeout=timeout)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"\n[!] {service.upper()} timed out after {timeout}s — skipping.")
        return -1
    except FileNotFoundError:
        print("[!] 'nxc' executable not found. Is netexec installed and on PATH?")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(130)
