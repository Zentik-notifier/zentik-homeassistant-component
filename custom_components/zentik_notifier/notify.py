from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

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


async def async_get_service_with_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = {**entry.data, **entry.options}
    user_ids = data.get(CONF_USER_IDS)
    if isinstance(user_ids, str):
        user_ids = [u.strip() for u in user_ids.split(",") if u.strip()] if user_ids else []
    elif not isinstance(user_ids, list):
        user_ids = []
    raw_name = data.get(CONF_NAME) or "zentik"
    service_name = f"zentik_notifier_{slugify(raw_name)}"
    display_name = f"Zentik notifier {raw_name}"
    return ZentikNotifyService(
        service_name=service_name,
        display_name=display_name,
        bucket_id=data[CONF_BUCKET_ID],
        access_token=data[CONF_ACCESS_TOKEN],
        server_url=data.get(CONF_SERVER_URL) or DEFAULT_SERVER_URL,
        user_ids=user_ids,
    )


class ZentikNotifyService(BaseNotificationService):
    def __init__(
        self,
        service_name: str,
        display_name: str,
        bucket_id: str,
        access_token: str,
        server_url: str,
        user_ids: list[str],
    ) -> None:
        self._service_name = service_name
        self._display_name = display_name
        self._bucket_id = bucket_id
        self._access_token = access_token
        self._server_url = server_url
        self._user_ids = user_ids or []

    @property
    def name(self) -> str:  # notify.<name>
        return self._service_name

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        title = kwargs.get(ATTR_TITLE) or kwargs.get("title") or self._display_name
        payload: dict[str, Any] = {
            "bucketId": self._bucket_id,
            "title": title,
            "message": message or kwargs.get(ATTR_MESSAGE) or "",
        }
        if self._user_ids:
            payload["userIds"] = self._user_ids
        for k, v in kwargs.items():
            if k in (ATTR_TITLE, ATTR_MESSAGE, "title"):
                continue
            payload.setdefault(k, v)
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self._server_url, json=payload, headers=headers, timeout=15) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        _LOGGER.error(
                            "Zentik notify failed (status=%s): %s", resp.status, text
                        )
        except Exception as err:  # pragma: no cover
            _LOGGER.exception("Zentik notify exception: %s", err)
