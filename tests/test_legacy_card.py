"""Tests for removing the card resource of versions up to 1.7 (fork only)."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest import TestCase

_PATH = Path(__file__).parents[1] / "custom_components" / "tesy" / "legacy_card.py"
_SPEC = spec_from_file_location("tesy_legacy_card", _PATH)
legacy = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = legacy
_SPEC.loader.exec_module(legacy)


class LegacyResourceTest(TestCase):
    def test_finds_old_integration_path_only(self):
        items = [
            {"id": "a", "url": "/tesy_static/tesy-boiler-card.js?v=183e0b81"},
            {"id": "b", "url": "/tesy_static/tesy-boiler-card.js"},
            {
                "id": "c",
                "url": "/hacsfiles/tesy-boiler-card/tesy-boiler-card.js?hacstag=1",
            },
            {"id": "d", "url": "/local/tesy-boiler-card.js"},
            {"url": "/tesy_static/tesy-boiler-card.js"},  # no id: cannot delete
            {"id": "e", "url": None},
        ]
        self.assertEqual(legacy.legacy_resource_ids(items), ["a", "b"])

    def test_nothing_to_remove(self):
        self.assertEqual(legacy.legacy_resource_ids([]), [])
