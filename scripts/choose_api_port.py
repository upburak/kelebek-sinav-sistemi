"""Choose an unused loopback port for the local Flask development server."""

from __future__ import annotations

import socket
import sys
from collections.abc import Iterable

DEFAULT_PORTS = range(5000, 5101)


def is_loopback_port_available(port: int) -> bool:
    """Return whether this process can bind the port on IPv4 loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def choose_api_port(candidates: Iterable[int] = DEFAULT_PORTS) -> int:
    """Return the first free candidate, without touching the process using others."""
    for port in candidates:
        if not 1 <= port <= 65535:
            continue
        if is_loopback_port_available(port):
            return port
    raise RuntimeError("127.0.0.1 üzerinde 5000–5100 aralığında boş API portu bulunamadı.")


if __name__ == "__main__":
    try:
        print(choose_api_port())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
