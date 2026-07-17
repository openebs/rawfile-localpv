import ipaddress
import warnings


def split_host_port(entry: str) -> tuple[str, str]:
    """Split a nameserver entry into ``(host, port)``.

    Accepts ``"8.8.8.8"``, ``"8.8.8.8:53"``, ``"::1"``, or
    ``"[2001:4860:4860::8888]:53"``. ``port`` is ``""`` when not present.
    """
    entry = entry.strip()
    if entry.startswith("["):  # bracketed IPv6, optionally "[addr]:port"
        host, _, port = entry[1:].partition("]")
        return host, port.lstrip(":")
    if entry.count(":") == 1:  # IPv4 "addr:port"
        host, _, port = entry.partition(":")
        return host, port
    return entry, ""  # bare IPv4 or bare (unbracketed) IPv6


def parse_nameservers(value) -> list[str]:
    """Normalize a nameserver spec into a list of valid ``ip[:port]`` entries.

    Accepts a comma-separated string or a list. Each entry must be a valid IP
    address (v4/v6) with an optional port in ``0..65535``. Invalid entries are
    dropped with a warning rather than raising, so a misconfigured value degrades
    to the remaining valid servers (or an empty list) instead of failing hard.
    """
    entries = (
        [s.strip() for s in value.split(",") if s.strip()]
        if isinstance(value, str)
        else value
    )
    valid = []
    for entry in entries or []:
        host, port = split_host_port(entry)
        try:
            ipaddress.ip_address(host)
            if port != "" and not (0 <= int(port) <= 65535):
                raise ValueError("port out of range")
        except ValueError:
            warnings.warn(f"Ignoring invalid DNS nameserver: {entry!r}")
            continue
        valid.append(entry)
    return valid
