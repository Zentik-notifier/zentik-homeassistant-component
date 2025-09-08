from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BUCKET_ID,
    CONF_ACCESS_TOKEN,
    CONF_SERVER_URL,
    CONF_NAME,
    CONF_USER_IDS,
    ATTR_TITLE,
    ATTR_MESSAGE,
    DEFAULT_SERVER_URL,
)

_LOGGER = logging.getLogger(__name__)


async def async_get_service(hass: HomeAssistant, config: dict, discovery_info=None):  # legacy path not used with config entries
    return None


async def async_get_service_with_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = {**entry.data, **entry.options}
    user_ids = data.get(CONF_USER_IDS)
    if isinstance(user_ids, str):
        user_ids = [u.strip() for u in user_ids.split(",") if u.strip()] if user_ids else []
    elif not isinstance(user_ids, list):
        user_ids = []
    return ZentikNotifyService(
        name=data.get(CONF_NAME) or "zentik",
        bucket_id=data[CONF_BUCKET_ID],
        access_token=data[CONF_ACCESS_TOKEN],
        server_url=data.get(CONF_SERVER_URL) or DEFAULT_SERVER_URL,
        user_ids=user_ids,
        session=aiohttp.ClientSession(),
    )


class ZentikNotifyService(BaseNotificationService):
    def __init__(self, name: str, bucket_id: str, access_token: str, server_url: str, user_ids: list[str], session: aiohttp.ClientSession):
        self._name = name
        self._bucket_id = bucket_id
        self._access_token = access_token
        self._server_url = server_url
        self._session = session
        self._user_ids = user_ids or []

    @property
    def name(self) -> str:  # pragma: no cover - trivial
        return self._name

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        title = kwargs.get(ATTR_TITLE) or kwargs.get("title") or self._name
        payload = {
            "bucketId": self._bucket_id,
            "title": title,
            "message": message or kwargs.get(ATTR_MESSAGE) or "",
        }
        if self._user_ids:
            payload["userIds"] = self._user_ids
        try:
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
            async with self._session.post(self._server_url, json=payload, headers=headers, timeout=15) as resp:
                if resp.status >= 400:
                    txt = await resp.text()
                    _LOGGER.error(
                        "Error sending Zentik notification (status=%s): %s", resp.status, txt
                    )
        except Exception as err:  # pragma: no cover - network errors
            _LOGGER.exception("Exception during sending Zentik notification: %s", err)

    async def async_remove(self):  # pragma: no cover - cleanup
        if not self._session.closed:
            await self._session.close()
