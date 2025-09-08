from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.helpers.entity import async_generate_entity_id

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up notify entity from a config entry."""
    data = {**entry.data, **entry.options}
    user_ids = data.get(CONF_USER_IDS)
    if isinstance(user_ids, str):
        user_ids = [u.strip() for u in user_ids.split(",") if u.strip()] if user_ids else []
    elif not isinstance(user_ids, list):
        user_ids = []
    raw_name = data.get(CONF_NAME) or "zentik"
    display_name = f"Zentik notifier {raw_name}"
    # Unique id: bucket|user1,user2 (sorted) or bucket|- if empty
    combo_key = ",".join(sorted(user_ids)) if user_ids else "-"
    unique_id = f"{data[CONF_BUCKET_ID]}|{combo_key}"
    entity = ZentikNotifyEntity(
        name=display_name,
        bucket_id=data[CONF_BUCKET_ID],
        access_token=data[CONF_ACCESS_TOKEN],
        server_url=data.get(CONF_SERVER_URL) or DEFAULT_SERVER_URL,
        user_ids=user_ids,
        session=aiohttp.ClientSession(),
        unique_id=unique_id,
    )
    object_id = f"zentik_notifier_{slugify(raw_name)}"
    entity.entity_id = async_generate_entity_id("notify.{}", object_id, hass=hass)
    async_add_entities([entity])


class ZentikNotifyEntity(NotifyEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        name: str,
        bucket_id: str,
        access_token: str,
        server_url: str,
        user_ids: list[str],
        session: aiohttp.ClientSession,
        unique_id: str | None,
    ) -> None:
        self._attr_name = name
        self._bucket_id = bucket_id
        self._access_token = access_token
        self._server_url = server_url
        self._session = session
        self._user_ids = user_ids or []
        self._attr_unique_id = unique_id

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        title = kwargs.get(ATTR_TITLE) or kwargs.get("title") or self._attr_name
        payload: dict[str, Any] = {
            "bucketId": self._bucket_id,
            "title": title,
            "message": message or kwargs.get(ATTR_MESSAGE) or "",
        }
        if self._user_ids:
            payload["userIds"] = self._user_ids
        # Merge other keys
        for k, v in kwargs.items():
            if k in (ATTR_TITLE, ATTR_MESSAGE, "title"):
                continue
            payload.setdefault(k, v)
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with self._session.post(self._server_url, json=payload, headers=headers, timeout=15) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    _LOGGER.error(
                        "Zentik notify failed (status=%s): %s", resp.status, text
                    )
        except Exception as err:  # pragma: no cover
            _LOGGER.exception("Zentik notify exception: %s", err)

    async def async_will_remove_from_hass(self) -> None:  # cleanup
        if not self._session.closed:
            await self._session.close()
