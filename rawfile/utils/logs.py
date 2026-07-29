import functools
import json
import sys
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from google.protobuf.json_format import MessageToDict
from loguru import logger as _logger
from loguru._defaults import LOGURU_FORMAT

logger = _logger


def fmt_k8s_exception(e: Exception):
    error_data = {
        "status": e.status,
        "reason": e.reason,
        "body": e.body,
    }
    return error_data


def fmt_exception(e: Exception):
    if all(key in e.__dict__ for key in ["status", "reason", "body"]):
        return fmt_k8s_exception(e)
    return str(e)


def _format_timedelta(td: timedelta):
    total_ms = int(td.total_seconds() * 1000)
    days, rem_ms = divmod(total_ms, 86400 * 1000)
    hours, rem_ms = divmod(rem_ms, 3600 * 1000)
    minutes, rem_ms = divmod(rem_ms, 60 * 1000)
    seconds, milliseconds = divmod(rem_ms, 1000)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    if milliseconds or not parts:
        parts.append(f"{milliseconds}ms")

    return " ".join(parts)


class _JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (tuple, set)):
            return list(o)
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, timedelta):
            return _format_timedelta(o)
        return super().default(o)


class LoggingFormats(StrEnum):
    JSON = "json"
    PRETTY = "pretty"


def _pretty_format(record) -> str:
    format = str(LOGURU_FORMAT)
    extra = record.get("extra", {})
    if extra and len(extra.keys()):
        format += " | {extra}"
    if record.get("exception", None):
        format += "\n{exception}"
    return str(format) + "\n"


def _json_serialize(record):
    subset = {
        "timestamp": record["time"],
        "level": record["level"].name,
        "caller": f"{record['name']}:{record['function']}:{record['line']}",
        "message": record["message"],
    }
    subset.update({k: v for k, v in record["extra"].items()})
    if record.get("exception", None):
        subset["exception"] = str(record["exception"])
    return json.dumps(subset, cls=_JSONEncoder)


def _json_sink(message):
    serialized = _json_serialize(message.record)
    sys.stdout.write(f"{serialized}\n")


_logging_handlers = {
    LoggingFormats.JSON: {"sink": _json_sink},
    LoggingFormats.PRETTY: {"sink": sys.stderr, "format": _pretty_format},
}

format = LoggingFormats.JSON
level = "INFO"


def init(_format: LoggingFormats, _level: str):
    logger.remove()
    global format, level
    format = _format
    level = _level
    logger.add(**_logging_handlers[format], level=level)


class GRPCLogger:
    def __init__(self, server_name: str) -> None:
        self._server_name = server_name

    def __call__(self, func):
        _server_name = self._server_name

        @functools.wraps(func)
        def wrap(self, request, context):
            start = datetime.now(UTC)
            is_json = format == LoggingFormats.JSON
            args = {
                "server_name": _server_name,
                "handler": func.__name__,
                "starttime": start,
            }
            res = None
            try:
                res = func(self, request, context)
                end = datetime.now(UTC)
                args.update(
                    {
                        "latency": end - start,
                        "endtime": end,
                        "success": True,
                    }
                )
                logger.success("GRPC Server Access Log", **args)
                return res
            except Exception:
                end = datetime.now(UTC)
                args.update(
                    {
                        "response": (MessageToDict(res) if is_json else res)
                        if res
                        else res,
                        "request": MessageToDict(request) if is_json else request,
                        "latency": end - start,
                        "endtime": end,
                        "success": False,
                        "state": {
                            "code": {
                                "name": context._state.code.name,
                                "value": context._state.code.value[0],
                                "description": context._state.code.value[1],
                            }
                            if context._state.code
                            else None,
                            "details": context._state.details.decode()
                            if context._state.details
                            else None,
                        },
                    }
                )
                logger.exception("GRPC Server Exception", **args)
                raise

        return wrap


__all__ = ["GRPCLogger", "format", "init", "logger"]
