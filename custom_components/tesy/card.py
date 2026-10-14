"""Serve the tesy-boiler-card Lovelace card from the integration.

The card file is served with ``Cache-Control: no-cache`` and an ETag, so
browsers and reverse proxies (Cloudflare, nginx caches) revalidate it on every
page load instead of keeping an old copy; an unchanged file costs a 304.

``/api/tesy/card_version`` reports the version this Home Assistant started
with. The card compares it with the ``?v=`` of the URL it was loaded from and
reloads a page that was opened before Home Assistant was restarted with a new
card (a wall tablet left open for days, say).
"""

from __future__ import annotations

import hashlib
from http import HTTPStatus
from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

CARD_URL = "/tesy_static/tesy-boiler-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "tesy-boiler-card.js"
VERSION_URL = "/api/tesy/card_version"


def card_hash(content: bytes) -> str:
    """Short content hash used as the card version."""
    return hashlib.sha256(content).hexdigest()[:8]


class TesyCardView(HomeAssistantView):
    """The card's JavaScript, always revalidated."""

    url = CARD_URL
    name = "tesy:card"
    requires_auth = False  # loaded by the browser like any frontend module

    def __init__(self, path: Path = CARD_PATH) -> None:
        """Serve the file at path."""
        self._path = path

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Return the card, or 304 if the browser already has this version."""
        hass: HomeAssistant = request.app["hass"]
        try:
            content = await hass.async_add_executor_job(self._path.read_bytes)
        except OSError:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        etag = f'"{card_hash(content)}"'
        headers = {"Cache-Control": "no-cache", "ETag": etag}
        if etag in request.headers.get("If-None-Match", ""):
            return web.Response(status=HTTPStatus.NOT_MODIFIED, headers=headers)
        return web.Response(
            body=content,
            content_type="application/javascript",
            charset="utf-8",
            headers=headers,
        )


class TesyCardVersionView(HomeAssistantView):
    """Version of the card this Home Assistant instance loads into pages."""

    url = VERSION_URL
    name = "api:tesy:card_version"

    def __init__(self, version: str) -> None:
        """Report version."""
        self._version = version

    async def get(self, request: web.Request) -> web.Response:
        """Return the version; never cached."""
        return web.json_response(
            {"version": self._version}, headers={"Cache-Control": "no-store"}
        )
