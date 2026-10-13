"""The Tesy integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed

from .coordinator import TesyCoordinator
from .const import (
    DOMAIN,
)

PLATFORMS: list[Platform] = [
    Platform.WATER_HEATER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tesy from a config entry."""
    coordinator = TesyCoordinator(
        entry.data,
        hass,
    )

    try:
        await coordinator.async_validate_input()
    except ConnectionError as connection_error:
        raise ConfigEntryAuthFailed from connection_error

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    if coordinator.supports_timezone:
        await coordinator.async_expected_timezone()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if coordinator.supports_timezone:
        # Keep the heater's time zone (it drives the weekly programs) in step
        # with Home Assistant: now, and whenever the HA time zone changes.
        await _async_sync_timezone(coordinator)

        @callback
        def _core_config_updated(event: Event) -> None:
            hass.async_create_task(_async_sync_timezone(coordinator))

        entry.async_on_unload(
            hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _core_config_updated)
        )

    return True


async def _async_sync_timezone(coordinator: TesyCoordinator) -> None:
    """Sync the heater time zone, logging instead of failing."""
    # Resolve the (possibly new) HA zone first so the clock sensor sees it.
    await coordinator.async_expected_timezone()
    coordinator.async_update_listeners()
    try:
        await coordinator.async_sync_timezone()
    except (ConnectionError, ValueError) as err:
        _LOGGER.warning("Could not sync the heater time zone: %s", err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
