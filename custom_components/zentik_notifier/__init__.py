from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


SERVICE_SEND = "send"

SERVICE_SEND_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("title"): vol.Any(str, None),
        vol.Required("message"): vol.Any(str, None),
        vol.Optional("data"): vol.Any(dict, list, str, int, float, bool, None),
    },
    extra=vol.PREVENT_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # pragma: no cover - minimal bootstrap
    async def _handle_send(call) -> None:
        from .notify import async_send_from_entry

        entry_id = call.data.get("entry_id")
        title = call.data.get("title")
        message = call.data.get("message") or ""
        extra = dict(call.data)

        entries = hass.config_entries.async_entries(DOMAIN)
        if entry_id:
            entries = [e for e in entries if e.entry_id == entry_id]

        for entry in entries:
            await async_send_from_entry(hass, entry, title, message, extra)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND):
        hass.services.async_register(DOMAIN, SERVICE_SEND, _handle_send, schema=SERVICE_SEND_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    from . import notify
    await notify.async_register_service(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Chiede al modulo notify di deregistrare il servizio
    from . import notify as notify_module
    await notify_module.async_unload_entry(hass, entry)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
