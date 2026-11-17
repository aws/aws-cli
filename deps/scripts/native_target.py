"""Reject dependency builds for a different host OS or architecture."""

import platform


def require_native_target(target: str) -> None:
    host_os = platform.system()
    machine = platform.machine().lower()
    host_arch = {"arm64": "aarch64", "amd64": "x86_64"}.get(machine, machine)
    allowed = host_arch in ("x86_64", "aarch64") and (
        host_os == "Linux"
        and target in (f"{host_arch}-linux-musl", f"{host_arch}-unknown-linux-musl")
        or host_os == "Darwin"
        and target in (f"{host_arch}-macos", f"{host_arch}-apple-darwin")
        or host_os == "Windows"
        and host_arch == "x86_64"
        and target in ("x86_64-windows-msvc", "x86_64-pc-windows-msvc")
    )
    if not allowed:
        raise SystemExit(
            f"native builds only: {host_os}/{host_arch} cannot build {target}"
        )
