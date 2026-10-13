"""DataUpdateCoordinator for the Tesy integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .tesy import Tesy
from .timezone import TZ_FIELD, posix_tz_for
from .tesy_oldapi import TesyOldApi
from .const import (
    ATTR_API,
    ATTR_CHILD_LOCK,
    DOMAIN,
    UPDATE_INTERVAL,
    USE_OLD_API,
)
import logging

_LOGGER = logging.getLogger(__name__)


class TesyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Tesy Coordinator class."""

    def __init__(self, data: dict[str, Any], hass: HomeAssistant) -> None:
        """Initialize."""
        if data.get(USE_OLD_API):
            self._client = TesyOldApi(data)
        else:
            self._client = Tesy(data)
        self._posix_tz_cache: dict[str, str | None] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def _validate(self) -> None:
        """Validate using Tesy API."""
        result = self._client.get_data()
        if result.get(ATTR_API) != "OK":
            raise ConnectionError
        return result

    async def async_validate_input(self) -> None:
        """Validate Tesy component."""
        return await self.hass.async_add_executor_job(self._validate)

    # Async update Data
    async def _async_update_data(self) -> dict[str, Any]:
        """Get new sensor data for Tesy component."""
        return await self.hass.async_add_executor_job(self._get_data)

    # Set target temperature in manual mode
    async def async_set_target_temperature(self, val: int) -> None:
        """Set target temperature for Tesy component."""
        return await self.hass.async_add_executor_job(
            self._client.set_target_temperature, val
        )

    # Turn power ON/OFF
    async def async_set_power(self, val: str) -> None:
        """Set power for Tesy component."""
        return await self.hass.async_add_executor_job(self._client.set_power, val)

    # Turn boost ON/OFF
    async def async_set_boost(self, val: str) -> None:
        """Set boost for Tesy component."""
        return await self.hass.async_add_executor_job(self._client.set_boost, val)

    # Turn operation mode
    async def async_set_operation_mode(self, val: str) -> None:
        """Set mode for Tesy component."""
        return await self.hass.async_add_executor_job(
            self._client.set_operation_mode, val
        )

    # Set child lock
    async def async_set_child_lock(self, val: str) -> None:
        """Set child lock for Tesy component."""
        return await self.hass.async_add_executor_job(self._client.set_child_lock, val)

    async def async_set_schedule(self, key: str, val: str) -> dict[str, Any]:
        """Write one day of a weekly program."""
        if self.is_old_api:
            raise NotImplementedError("Schedules are not supported by the old API")
        return await self.hass.async_add_executor_job(
            self._client.set_schedule, key, val
        )

    @property
    def supports_timezone(self) -> bool:
        """Return True if the device exposes a writable POSIX time zone."""
        return not self.is_old_api and TZ_FIELD in (self.data or {})

    @property
    def expected_timezone(self) -> str | None:
        """POSIX TZ string for Home Assistant's zone, once resolved."""
        return self._posix_tz_cache.get(self.hass.config.time_zone)

    async def async_expected_timezone(self) -> str | None:
        """Return the POSIX TZ string matching Home Assistant's time zone."""
        name = self.hass.config.time_zone
        if name not in self._posix_tz_cache:
            self._posix_tz_cache[name] = await self.hass.async_add_executor_job(
                posix_tz_for, name
            )
        return self._posix_tz_cache[name]

    async def async_sync_timezone(self) -> bool:
        """Write Home Assistant's time zone to the device if it differs.

        Returns True if the device was changed.
        """
        if not self.supports_timezone:
            return False
        expected = await self.async_expected_timezone()
        if expected is None:
            raise ValueError(
                f"No POSIX time zone found for {self.hass.config.time_zone}"
            )
        if self.data.get(TZ_FIELD) == expected:
            return False

        response = await self.hass.async_add_executor_job(
            self._client.set_timezone, expected
        )
        if response.get(ATTR_API) != "OK" or response.get(TZ_FIELD) != expected:
            raise ConnectionError(f"Heater rejected time zone {expected}: {response}")

        _LOGGER.info(
            "Tesy time zone changed from %s to %s", self.data.get(TZ_FIELD), expected
        )
        self.data[TZ_FIELD] = expected
        self.async_set_updated_data(self.data)
        return True

    async def async_reset_energy_counter(self) -> dict[str, Any]:
        """Reset the resettable energy counter."""
        return await self.hass.async_add_executor_job(self._client.reset_energy_counter)

    def _get_data(self) -> dict[str, Any]:
        """Get new sensor data using Tesy API."""
        try:
            return self._client.get_data()
        except ConnectionError as http_error:
            raise UpdateFailed from http_error

    def get_config_power(self) -> int:
        return self._client._heater_power

    @property
    def is_old_api(self) -> bool:
        """Return True if the device is accessed via the old (unofficial) API."""
        return isinstance(self._client, TesyOldApi)
