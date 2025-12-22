from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.util import slugify

from .const import (
    CONF_BUCKET_ID,
    CONF_ACCESS_TOKEN,
    CONF_SERVER_URL,
    CONF_NAME,
    CONF_USER_IDS,
    CONF_MAGIC_CODE,
    ATTR_TITLE,
    ATTR_MESSAGE,
    DEFAULT_SERVER_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_RESERVED_SERVICE_KEYS: set[str] = {
    ATTR_MESSAGE,
    ATTR_TITLE,
    "data",
    "entry_id",
    "magicCode",
}


ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("type"): cv.string,
        vol.Optional("value"): cv.string,
        vol.Optional("destructive"): cv.boolean,
        vol.Optional("icon"): cv.string,
        vol.Optional("title"): cv.string,
    },
    extra=vol.PREVENT_EXTRA,
)


ATTACHMENT_SCHEMA = vol.Schema(
    {
        vol.Optional("mediaType"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("url"): cv.string,
        vol.Optional("attachmentUuid"): cv.string,
        vol.Optional("saveOnServer"): cv.boolean,
    },
    extra=vol.PREVENT_EXTRA,
)


ATTACHMENT_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional("mediaType"): cv.string,
        vol.Optional("name"): cv.string,
    },
    extra=vol.PREVENT_EXTRA,
)

# Schema for the notify.<service_name> call
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_MESSAGE, default=""): cv.string,
        vol.Optional("data"): dict,
        vol.Optional("subtitle"): cv.string,
        vol.Optional("collapseId"): cv.string,
        vol.Optional("groupId"): cv.string,
        vol.Optional("userIds"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("imageUrl"): cv.string,
        vol.Optional("videoUrl"): cv.string,
        vol.Optional("gifUrl"): cv.string,
        vol.Optional("tapUrl"): cv.string,
        vol.Optional("sound"): cv.string,
        vol.Optional("deliveryType"): cv.string,
        vol.Optional("addMarkAsReadAction"): cv.boolean,
        vol.Optional("addOpenNotificationAction"): cv.boolean,
        vol.Optional("addDeleteAction"): cv.boolean,
        vol.Optional("actions"): vol.All(cv.ensure_list, [ACTION_SCHEMA]),
        vol.Optional("tapAction"): ACTION_SCHEMA,
        vol.Optional("attachments"): vol.All(cv.ensure_list, [ATTACHMENT_SCHEMA]),
        vol.Optional("attachmentUuids"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("attachmentOptions"): ATTACHMENT_OPTIONS_SCHEMA,
        vol.Optional("snoozes"): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional("postpones"): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional("locale"): cv.string,
        vol.Optional("remindEveryMinutes"): vol.Coerce(int),
        vol.Optional("maxReminders"): vol.Coerce(int),
        vol.Optional("executionId"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
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
    bucket_id = data.get(CONF_BUCKET_ID)
    access_token = data.get(CONF_ACCESS_TOKEN)
    magic_code = data.get(CONF_MAGIC_CODE)
    server_url = data.get(CONF_SERVER_URL) or DEFAULT_SERVER_URL

    if not magic_code and not (bucket_id and access_token):
        _LOGGER.error(
            "Invalid Zentik configuration for entry_id=%s: provide bucket_id+access_token or magic_code",
            entry.entry_id,
        )
        return

    payload: dict[str, Any] = {
        "title": title or raw_name,
    }

    if message:
        payload["body"] = message

    if magic_code:
        payload["magicCode"] = magic_code
    else:
        payload["bucketId"] = bucket_id

    if (custom_data := extra.get("data")) is not None:
        if isinstance(custom_data, dict):
            for dk, dv in custom_data.items():
                if dk in ("bucketId", "title", "body", "magicCode"):
                    continue
                payload.setdefault(dk, dv)
        else:
            payload.setdefault("data", custom_data)

    # Copy explicit top-level keys (from service call) into the payload.
    for key, value in extra.items():
        if key in _RESERVED_SERVICE_KEYS:
            continue
        if key in ("bucketId", "title", "body", "magicCode"):
            continue
        if value is None:
            continue
        payload[key] = value

    if user_ids:
        payload["userIds"] = user_ids

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

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
        title = data_call.get(ATTR_TITLE)
        message = data_call.get(ATTR_MESSAGE, "")
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
