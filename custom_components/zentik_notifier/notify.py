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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:  # type: ignore[override]
    """Register a classic notify.<service_name> without creating an entity."""
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

    bucket_id = data[CONF_BUCKET_ID]
    access_token = data[CONF_ACCESS_TOKEN]
    server_url = data.get(CONF_SERVER_URL) or DEFAULT_SERVER_URL

    async def _async_send(title: str | None, message: str, extra: dict[str, Any]) -> None:
        payload: dict[str, Any] = {
            "bucketId": bucket_id,
            "title": title or raw_name,
            "body": message or "",
        }
        if (custom_data := extra.get("data")) is not None:
            # Se dict appiattiamo chiave per chiave; altrimenti manteniamo come 'data'
            if isinstance(custom_data, dict):
                for dk, dv in custom_data.items():
                    if dk in ("bucketId", "title", "body"):  # non sovrascrivere core
                        continue
                    payload.setdefault(dk, dv)
            else:
                payload.setdefault("data", custom_data)
        if user_ids:
            payload["userIds"] = user_ids
    # Nessuna fusione di altre chiavi extra: schema limita i campi.
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
                            "Zentik notify failed (service=%s status=%s): %s", service_name, resp.status, text
                        )
        except Exception:  # pragma: no cover
            _LOGGER.exception("Zentik notify exception (service=%s)", service_name)

    async def _handle_service(call: ServiceCall) -> None:
        data_call = dict(call.data)
        title = data_call.get(ATTR_TITLE) or data_call.get("title")
        message = data_call.get(ATTR_MESSAGE) or data_call.get("message") or ""
        await _async_send(title, message, data_call)

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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # pragma: no cover - simple
    info = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if info:
        service_name = info.get("service_name")
        if service_name and hass.services.has_service("notify", service_name):
            hass.services.async_remove("notify", service_name)
            _LOGGER.info("Unregistered notify service notify.%s", service_name)
    return True
