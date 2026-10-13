"""Tests for device clock / time zone helpers (no Home Assistant needed)."""

from datetime import datetime, timedelta, timezone as dt_timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase

_PATH = Path(__file__).parents[1] / "custom_components" / "tesy" / "timezone.py"
_SPEC = spec_from_file_location("tesy_timezone", _PATH)
tz = module_from_spec(_SPEC)
_SPEC.loader.exec_module(tz)

# Value reported by a ModEco 2 (id 2004) set up for Kyiv / Sofia.
KYIV = "EET-2EEST,M3.5.0/3,M10.5.0/4"
LOCAL_NOW = datetime(2026, 10, 13, 23, 48, 50, tzinfo=dt_timezone(timedelta(hours=3)))


def data(date="2026-10-13 23:48:48", zone=KYIV):
    return {"date": date, "tz": zone}


class PosixTzTest(TestCase):
    """Derive the POSIX string from the tz database."""

    def test_kyiv_matches_device(self):
        self.assertEqual(tz.posix_tz_for("Europe/Kyiv"), KYIV)
        self.assertEqual(tz.posix_tz_for("Europe/Sofia"), KYIV)

    def test_other_zones(self):
        self.assertEqual(tz.posix_tz_for("UTC"), "UTC0")
        self.assertEqual(tz.posix_tz_for("Europe/Berlin"), "CET-1CEST,M3.5.0,M10.5.0/3")

    def test_rejects_bad_names(self):
        for name in (None, "", "../etc/passwd", "Europe/../../etc", "Nowhere/City"):
            self.assertIsNone(tz.posix_tz_for(name))

    def test_footer_parsing(self):
        self.assertEqual(
            tz.posix_tz_from_tzif(b"TZif2...\n" + KYIV.encode() + b"\n"), KYIV
        )
        self.assertIsNone(
            tz.posix_tz_from_tzif(b"TZif\0...\nUTC0\n")
        )  # v1 has no footer
        self.assertIsNone(tz.posix_tz_from_tzif(b"nope"))
        self.assertIsNone(tz.posix_tz_from_tzif(b"TZif2...\nbad value\n"))


class ClockProblemTest(TestCase):
    """Detect a wrong time zone or a drifting clock."""

    def test_in_sync(self):
        self.assertEqual(tz.clock_problems(data(), KYIV, LOCAL_NOW), [])
        self.assertEqual(tz.clock_offset(data(), LOCAL_NOW), -2.0)

    def test_wrong_timezone(self):
        # Module left on Berlin time: local clock one hour behind Kyiv.
        stale = data(date="2026-10-13 22:48:48", zone="CET-1CEST,M3.5.0,M10.5.0/3")
        self.assertEqual(
            tz.clock_problems(stale, KYIV, LOCAL_NOW), ["timezone", "offset"]
        )

    def test_drift_without_internet(self):
        drifted = data(date="2026-10-13 23:40:00")
        self.assertEqual(tz.clock_problems(drifted, KYIV, LOCAL_NOW), ["offset"])

    def test_unknown_values_are_not_problems(self):
        self.assertEqual(tz.clock_problems({}, KYIV, LOCAL_NOW), [])
        self.assertEqual(tz.clock_problems(data(), None, LOCAL_NOW), [])
        self.assertIsNone(tz.clock_offset({"date": "garbage"}, LOCAL_NOW))
