from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from app import __version__

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:8080",
    "http://127.0.0.1:8080",
)


def _parse_port(raw_value: str) -> int:
    try:
        port = int(raw_value)
    except ValueError as error:
        raise ValueError("JACK_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ValueError("JACK_PORT must be between 1 and 65535.")
    return port


def _parse_log_level(raw_value: str) -> tuple[str, int]:
    name = raw_value.strip().upper()
    level = logging.getLevelName(name)
    if not isinstance(level, int):
        raise ValueError("JACK_LOG_LEVEL must be a valid logging level.")
    return name, level


def _parse_cors_origins(raw_value: str) -> tuple[str, ...]:
    origins = tuple(origin.strip() for origin in raw_value.split(",") if origin.strip())
    for origin in origins:
        parsed = urlsplit(origin)
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError(f"Invalid local CORS origin: {origin}") from error

        if (
            parsed.scheme != "http"
            or parsed.hostname not in _LOCAL_HOSTS
            or port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "CORS origins must be explicit http://localhost or loopback "
                "origins with a port."
            )
    return origins


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    log_level_name: str
    log_level: int
    cors_origins: tuple[str, ...]
    app_name: str = "J.A.C.K. Local Backend"
    version: str = __version__

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv(_BACKEND_DIR / ".env", override=False)

        environment = os.getenv("JACK_ENV", "development").strip().lower()
        host = os.getenv("JACK_HOST", "127.0.0.1").strip().lower()
        if host != "127.0.0.1":
            raise ValueError(
                "JACK_HOST must be 127.0.0.1; the backend only binds to IPv4 localhost."
            )

        log_level_name, log_level = _parse_log_level(
            os.getenv("JACK_LOG_LEVEL", "INFO")
        )
        cors_origins = _parse_cors_origins(
            os.getenv(
                "JACK_CORS_ORIGINS",
                ",".join(_DEFAULT_CORS_ORIGINS),
            )
        )

        return cls(
            environment=environment,
            host=host,
            port=_parse_port(os.getenv("JACK_PORT", "8000")),
            log_level_name=log_level_name,
            log_level=log_level,
            cors_origins=cors_origins,
        )


settings = Settings.from_environment()

