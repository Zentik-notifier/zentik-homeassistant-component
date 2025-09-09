from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # pragma: no cover - minimal bootstrap
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    # Il servizio notify.<name> viene registrato in notify.async_setup_entry
    # Importiamo dinamicamente per assicurarci che il modulo esegua la registrazione.
    from . import notify  # noqa: F401
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Chiede al modulo notify di deregistrare il servizio
    from . import notify as notify_module
    await notify_module.async_unload_entry(hass, entry)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
