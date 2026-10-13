"""Device clock and time zone helpers for the Tesy local API.

The ESP32 module takes UTC from the network and converts it to local time with
a POSIX TZ string held in ``tz`` (``EET-2EEST,M3.5.0/3,M10.5.0/4`` for Kyiv).
That field can be written with ``/api?name=tz&set=<string>``; the clock itself
cannot be set over the API.

The POSIX string for an IANA zone is the footer line of its TZif v2+ file, so
it is read from the same tz database that Python's ``zoneinfo`` uses.

This module has no Home Assistant dependencies so it can be unit tested alone.
"""

from __future__ import annotations

from datetime import datetime
from importlib import resources
from pathlib import Path
import re
import zoneinfo

TZ_FIELD = "tz"
DATE_FIELD = "date"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Clock offset (device local time vs Home Assistant local time) that counts as
# a problem. Polling and network delays stay well below this.
MAX_CLOCK_OFFSET = 300

_POSIX_TZ = re.compile(r"^[A-Za-z<][-+A-Za-z0-9<>,./:]*$")
_IANA_NAME = re.compile(r"^[A-Za-z0-9_+-]+(/[A-Za-z0-9_+-]+)*$")


def posix_tz_from_tzif(content: bytes) -> str | None:
    """Return the POSIX TZ footer of a TZif v2+ file, or None."""
    if not content.startswith(b"TZif") or len(content) < 5 or content[4:5] < b"2":
        return None
    if not content.endswith(b"\n"):
        return None
    start = content.rfind(b"\n", 0, len(content) - 1)
    if start < 0:
        return None
    footer = content[start + 1 : -1].decode("ascii", "ignore")
    return footer if footer and _POSIX_TZ.match(footer) else None


def _tzif_candidates(name: str):
    parts = name.split("/")
    for root in zoneinfo.TZPATH:
        yield Path(root, *parts)
    try:
        yield resources.files("tzdata.zoneinfo").joinpath(*parts)
    except ModuleNotFoundError:
        return


def posix_tz_for(name: str | None) -> str | None:
    """Return the POSIX TZ string for an IANA zone name such as Europe/Kyiv."""
    if not name or not _IANA_NAME.match(name) or ".." in name:
        return None
    for path in _tzif_candidates(name):
        try:
            content = path.read_bytes()
        except (OSError, ValueError):
            continue
        result = posix_tz_from_tzif(content)
        if result:
            return result
    return None


def device_time(data: dict) -> datetime | None:
    """Return the device local time from the ``date`` field (naive)."""
    value = data.get(DATE_FIELD)
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        return None


def clock_offset(data: dict, local_now: datetime) -> float | None:
    """Seconds the device clock is ahead (+) of Home Assistant's local time."""
    device = device_time(data)
    if device is None:
        return None
    return (device - local_now.replace(tzinfo=None)).total_seconds()


def clock_problems(
    data: dict, expected_tz: str | None, local_now: datetime
) -> list[str]:
    """Return the clock problems found: ``timezone`` and/or ``offset``."""
    problems = []
    current_tz = data.get(TZ_FIELD)
    if expected_tz and current_tz is not None and current_tz != expected_tz:
        problems.append("timezone")
    offset = clock_offset(data, local_now)
    if offset is not None and abs(offset) > MAX_CLOCK_OFFSET:
        problems.append("offset")
    return problems
