import shlex
from typing import Any


def build_command(service: str, cfg: dict[str, Any]) -> list[str]:
    """Return the full nxc argument list for *service* from *cfg*."""
    cmd: list[str] = ["nxc", service]

    if target := (cfg.get("target") or ""):
        cmd.append(target)

    if username := (cfg.get("username") or ""):
        cmd.extend(["-u", username])

    if password := (cfg.get("password") or ""):
        cmd.extend(["-p", password])

    _append_global_flags(cmd, cfg.get("global_flags", {}))

    if svc_flags := cfg.get("service_flags", {}).get(service, ""):
        cmd.extend(shlex.split(svc_flags))

    return cmd


def _append_global_flags(cmd: list[str], gf: dict[str, Any]) -> None:
    """Mutate *cmd* by appending all active global nxc flags from *gf*."""
    if gf.get("hash"):
        cmd.extend(["-H", str(gf["hash"])])
    if gf.get("cred_id") is not None:
        cmd.extend(["-id", str(gf["cred_id"])])
    if gf.get("threads") is not None:
        cmd.extend(["-t", str(gf["threads"])])
    if gf.get("timeout") is not None:
        cmd.extend(["--timeout", str(gf["timeout"])])
    if gf.get("jitter"):
        cmd.extend(["--jitter", str(gf["jitter"])])
    if gf.get("no_progress"):
        cmd.append("--no-progress")
    if gf.get("log"):
        cmd.extend(["--log", str(gf["log"])])
    if gf.get("verbose"):
        cmd.append("--verbose")
    if gf.get("debug"):
        cmd.append("--debug")
    if gf.get("ipv6"):
        cmd.append("-6")
    if gf.get("dns_server"):
        cmd.extend(["--dns-server", str(gf["dns_server"])])
    if gf.get("dns_tcp"):
        cmd.append("--dns-tcp")
    if gf.get("dns_timeout") is not None:
        cmd.extend(["--dns-timeout", str(gf["dns_timeout"])])
    if gf.get("ignore_pw_decoding"):
        cmd.append("--ignore-pw-decoding")
    if gf.get("no_bruteforce"):
        cmd.append("--no-bruteforce")
    if gf.get("continue_on_success"):
        cmd.append("--continue-on-success")
    if gf.get("gfail_limit") is not None:
        cmd.extend(["--gfail-limit", str(gf["gfail_limit"])])
    if gf.get("ufail_limit") is not None:
        cmd.extend(["--ufail-limit", str(gf["ufail_limit"])])
    if gf.get("fail_limit") is not None:
        cmd.extend(["--fail-limit", str(gf["fail_limit"])])
    if gf.get("kerberos"):
        cmd.append("-k")
    if gf.get("use_kcache"):
        cmd.append("--use-kcache")
    if gf.get("aes_key"):
        cmd.extend(["--aesKey", str(gf["aes_key"])])
    if gf.get("kdc_host"):
        cmd.extend(["--kdcHost", str(gf["kdc_host"])])
    if gf.get("pfx_cert"):
        cmd.extend(["--pfx-cert", str(gf["pfx_cert"])])
    if gf.get("pfx_base64"):
        cmd.extend(["--pfx-base64", str(gf["pfx_base64"])])
    if gf.get("pfx_pass"):
        cmd.extend(["--pfx-pass", str(gf["pfx_pass"])])
    if gf.get("pem_cert"):
        cmd.extend(["--pem-cert", str(gf["pem_cert"])])
    if gf.get("pem_key"):
        cmd.extend(["--pem-key", str(gf["pem_key"])])
    if gf.get("module"):
        cmd.extend(["-M", str(gf["module"])])
    if gf.get("module_options"):
        cmd.extend(["-o", str(gf["module_options"])])
