import os
import shlex
import subprocess
import sys
import threading

_SEP = "─" * 64


def run_service(
    service: str, cmd: list[str], timeout: int | None, stream_output: bool = False
) -> int:
    """Invoke nxc for *service* and return its exit code.

    Returns ``-1`` when the process is killed by *timeout*. Exits the whole
    program on ``KeyboardInterrupt`` or if the ``nxc`` binary is not found.
    """
    print(f"\n{_SEP}")
    print(f"  Protocol : {service.upper()}")
    print(f"  Command  : {shlex.join(cmd)}")
    if timeout:
        print(f"  Timeout  : {timeout}s")
    print(_SEP)

    env = os.environ.copy()
    if stream_output:
        env["PYTHONUNBUFFERED"] = "1"
        # nxc detects the pipe and disables Rich colours; override that.
        env["FORCE_COLOR"] = "1"

    process: subprocess.Popen[str] | None = None

    try:
        if stream_output:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            assert process.stdout is not None

            # A timer kills the process after `timeout` seconds.  We cannot
            # rely on process.wait(timeout=…) here because that is only called
            # after the stdout loop finishes — i.e., after the process has
            # already exited — so it would never actually enforce a limit.
            timed_out = False
            timer: threading.Timer | None = None

            if timeout:

                def _timeout_kill() -> None:
                    nonlocal timed_out
                    timed_out = True
                    process.kill()  # type: ignore[union-attr]

                timer = threading.Timer(timeout, _timeout_kill)
                timer.start()

            try:
                for line in process.stdout:
                    sys.stdout.write(line)
            finally:
                if timer is not None:
                    timer.cancel()

            process.wait()

            if timed_out:
                print(f"\n[!] {service.upper()} timed out after {timeout}s — skipping.")
                return -1

            return process.returncode

        else:
            result = subprocess.run(cmd, timeout=timeout)
            return result.returncode

    except subprocess.TimeoutExpired:
        # Only reachable from the non-streaming subprocess.run() path.
        if process is not None:
            process.kill()
            process.wait()
        print(f"\n[!] {service.upper()} timed out after {timeout}s — skipping.")
        return -1
    except FileNotFoundError:
        print("[!] 'nxc' executable not found. Is netexec installed and on PATH?")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(130)
