from __future__ import annotations

from zoneinfo import available_timezones


def list_timezones() -> list[str]:
    return sorted(available_timezones())
