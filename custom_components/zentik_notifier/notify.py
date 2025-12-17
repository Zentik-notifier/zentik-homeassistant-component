from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
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
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Schema for the notify.<service_name> call
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_TITLE): vol.Any(str, None),
        vol.Required(ATTR_MESSAGE, default=""): vol.Any(str, None),
        vol.Optional("data"): vol.Any(dict, list, str, int, float, bool, None),
    },
    extra=vol.PREVENT_EXTRA,
)


async def async_send_from_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    title: str | None,
    message: str,
    extra: dict[str, Any],
) -> None:
    """Send a notification using the given config entry."""
    data = {**entry.data, **entry.options}

    user_ids = data.get(CONF_USER_IDS)
    if isinstance(user_ids, str):
        user_ids = [u.strip() for u in user_ids.split(",") if u.strip()] if user_ids else []
    elif not isinstance(user_ids, list):
        user_ids = []

    raw_name = data.get(CONF_NAME) or "zentik"
    bucket_id = data[CONF_BUCKET_ID]
    access_token = data[CONF_ACCESS_TOKEN]
    server_url = data.get(CONF_SERVER_URL) or DEFAULT_SERVER_URL

    payload: dict[str, Any] = {
        "bucketId": bucket_id,
        "title": title or raw_name,
        "body": message or "",
    }

    if (custom_data := extra.get("data")) is not None:
        if isinstance(custom_data, dict):
            for dk, dv in custom_data.items():
                if dk in ("bucketId", "title", "body"):
                    continue
                payload.setdefault(dk, dv)
        else:
            payload.setdefault("data", custom_data)

    if user_ids:
        payload["userIds"] = user_ids

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(server_url, json=payload, headers=headers, timeout=15) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    _LOGGER.error(
                        "Zentik notify failed (entry_id=%s status=%s): %s",
                        entry.entry_id,
                        resp.status,
                        text,
                    )
    except Exception:  # pragma: no cover
        _LOGGER.exception("Zentik notify exception (entry_id=%s)", entry.entry_id)


async def async_register_service(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Register the notify.<service_name> service for this config entry."""
    # Merge data & options
    data = {**entry.data, **entry.options}

    # Normalize user ids
    user_ids = data.get(CONF_USER_IDS)
    if isinstance(user_ids, str):
        user_ids = [u.strip() for u in user_ids.split(",") if u.strip()] if user_ids else []
    elif not isinstance(user_ids, list):
        user_ids = []

    raw_name = data.get(CONF_NAME) or "zentik"
    service_name = f"zentik_notifier_{slugify(raw_name)}"

    async def _handle_service(call: ServiceCall) -> None:
        data_call = dict(call.data)
        title = data_call.get(ATTR_TITLE) or data_call.get("title")
        message = data_call.get(ATTR_MESSAGE) or data_call.get("message") or ""
        await async_send_from_entry(hass, entry, title, message, data_call)

    # Register the service under domain 'notify'
    if hass.services.has_service("notify", service_name):
        _LOGGER.debug("Service notify.%s already exists; replacing", service_name)
        hass.services.async_remove("notify", service_name)

    hass.services.async_register(
        "notify", service_name, _handle_service, schema=SERVICE_SCHEMA
    )

    # Store reference for unload
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "service_name": service_name,
        **data,
    }

    _LOGGER.info("Registered notify service notify.%s", service_name)
    return True


# Optional platform-style entry point (not used now, but kept for compatibility)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities=None) -> bool:  # type: ignore[override]
    return await async_register_service(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # pragma: no cover - simple
    info = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if info:
        service_name = info.get("service_name")
        if service_name and hass.services.has_service("notify", service_name):
            hass.services.async_remove("notify", service_name)
            _LOGGER.info("Unregistered notify service notify.%s", service_name)
    return True
