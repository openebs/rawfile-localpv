from .model import RawFileCmd

config: RawFileCmd = RawFileCmd()  # type: ignore ## Pydantic handles inputs

__all__ = ["config"]
