"""Tests for per-model extended features (no Home Assistant needed)."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import TestCase

_PATH = Path(__file__).parents[1] / "custom_components" / "tesy" / "features.py"
_SPEC = spec_from_file_location("tesy_features", _PATH)
features = module_from_spec(_SPEC)
_SPEC.loader.exec_module(features)

ALL = {features.FEATURE_SCHEDULE, features.FEATURE_TIMEZONE, features.FEATURE_CARD}


class DeviceFeaturesTest(TestCase):
    def test_modeco2_gets_everything(self):
        data = {
            "id": "2004",
            "prgP1MO": "FF" * 24,
            "tz": "EET-2EEST,M3.5.0/3,M10.5.0/4",
        }
        self.assertEqual(features.device_features(data), ALL)

    def test_other_models_get_nothing(self):
        # Same fields, but the model is not verified: basic behaviour.
        for model in ("2000", "2002", "2003", "2005", None):
            data = {"id": model, "prgP1MO": "FF" * 24, "tz": "UTC0"}
            self.assertEqual(features.device_features(data), frozenset(), model)

    def test_missing_fields_disable_their_feature(self):
        self.assertEqual(
            features.device_features({"id": "2004"}), {features.FEATURE_CARD}
        )
        self.assertEqual(
            features.device_features({"id": 2004, "tz": "UTC0"}),
            {features.FEATURE_TIMEZONE, features.FEATURE_CARD},
        )

    def test_no_data(self):
        self.assertEqual(features.device_features(None), frozenset())
