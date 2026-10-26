"""Clean up after the thermostat card that versions up to 1.7 served.

The card used to be served by the integration at /tesy_static/ and added to
the dashboard resources automatically. It is now installed on its own through
HACS (https://github.com/pollstar/tesy-boiler-card), so the old resource would
point to a file that no longer exists and make dashboards report an error.
It is removed once, on the first setup after the update.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

LEGACY_CARD_PATH = "/tesy_static/tesy-boiler-card.js"
_DONE = "tesy_legacy_card_checked"


def legacy_resource_ids(items: list[dict[str, Any]]) -> list[str]:
    """Ids of resources that load the card from the old integration path."""
    return [
        str(item["id"])
        for item in items
        if "id" in item
        and urlsplit(str(item.get("url") or "")).path == LEGACY_CARD_PATH
    ]


async def async_remove_legacy_card_resource(hass: HomeAssistant) -> None:
    """Remove the old card resource from storage-mode dashboards, once."""
    if hass.data.get(_DONE):
        return
    hass.data[_DONE] = True
    data = hass.data.get("lovelace")
    if data is None:
        return
    if isinstance(data, dict):  # older Home Assistant
        mode = data.get("resource_mode") or data.get("mode")
        resources = data.get("resources")
    else:
        mode = getattr(data, "resource_mode", None) or getattr(data, "mode", None)
        resources = getattr(data, "resources", None)
    if mode != "storage" or not hasattr(resources, "async_delete_item"):
        return
    try:
        await resources.async_get_info()  # loads the stored resources
        for item_id in legacy_resource_ids(list(resources.async_items())):
            await resources.async_delete_item(item_id)
            _LOGGER.info(
                "Removed the old Tesy card resource %s; install the card from "
                "https://github.com/pollstar/tesy-boiler-card",
                LEGACY_CARD_PATH,
            )
    except Exception:  # noqa: BLE001 - never block setup over the cleanup
        _LOGGER.warning("Could not remove the old Tesy card resource", exc_info=True)
