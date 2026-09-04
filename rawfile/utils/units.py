import re
from collections.abc import Mapping
from datetime import timedelta


def pretty_size_to_bytes(pretty_size: str):
    """
    Converts a human-readable size string (e.g., "2GB", "500MB", "1.5KB", "5GiB")
    to its equivalent value in bytes.
    """
    pretty_size = pretty_size.strip().upper()
    if not len(pretty_size):
        return 0

    units = {
        "B": 1,
        "KiB": 1024,
        "KB": 1000,
        "MiB": 1024**2,
        "MB": 1000**2,
        "GiB": 1024**3,
        "GB": 1000**3,
        "TiB": 1024**4,
        "TB": 1000**4,
        "PiB": 1024**5,
        "PB": 1000**5,
    }
    for unit, multiplier in reversed(units.items()):
        if pretty_size.endswith(unit):
            try:
                value_str = pretty_size[: -len(unit)].strip()
                value = float(value_str)
                return int(value * multiplier)
            except ValueError:
                return 0
    return int(pretty_size)


def str_to_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower().strip() in ("1", "t", "true", "yes", "y", "on")


def normalize_value(value: str) -> str | None:
    _value = value.strip()
    if len(_value) == 0 or _value.lower() in ("none", "null", "nil"):
        return None
    return _value.strip()


def normalize_parameters(parameters: Mapping[str, str]) -> Mapping[str, str]:
    normalized: dict[str, str] = {}
    for k, v in parameters.items():
        normalized_value = normalize_value(v)
        if normalized_value is not None:
            normalized[k.lower()] = normalized_value
    return normalized


def parse_time_delta(time_str: str) -> timedelta:
    pattern = r"(?P<value>\d+)(?P<unit>[dhms])"
    matches = re.findall(pattern, time_str.lower())

    if not matches:
        raise ValueError(f"Invalid delta format: '{time_str}'")

    total = timedelta()
    for value, unit in matches:
        value = int(value)
        if unit == "d":
            total += timedelta(days=value)
        elif unit == "h":
            total += timedelta(hours=value)
        elif unit == "m":
            total += timedelta(minutes=value)
        elif unit == "s":
            total += timedelta(seconds=value)
    return total
