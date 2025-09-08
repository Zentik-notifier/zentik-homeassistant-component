from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_BUCKET_ID,
    CONF_ACCESS_TOKEN,
    CONF_SERVER_URL,
    CONF_NAME,
    CONF_USER_IDS,
    DEFAULT_SERVER_URL,
)


class ZentikNotifierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestione del flusso di configurazione per Zentik Notifier."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Unicità: usiamo bucket_id come unique_id (se duplicato -> abort)
            await self.async_set_unique_id(user_input[CONF_BUCKET_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_BUCKET_ID): str,
                vol.Required(CONF_ACCESS_TOKEN): str,
                vol.Optional(CONF_SERVER_URL, default=DEFAULT_SERVER_URL): str,
                vol.Optional(CONF_USER_IDS, default=""): str,  # comma separated
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):  # pragma: no cover - simple delegation
        return ZentikNotifierOptionsFlow(config_entry)


class ZentikNotifierOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        data = {**self.entry.data, **self.entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=data.get(CONF_NAME)): str,
                vol.Required(CONF_BUCKET_ID, default=data.get(CONF_BUCKET_ID)): str,
                vol.Required(CONF_ACCESS_TOKEN, default=data.get(CONF_ACCESS_TOKEN)): str,
                vol.Optional(
                    CONF_SERVER_URL,
                    default=data.get(CONF_SERVER_URL, DEFAULT_SERVER_URL),
                ): str,
                vol.Optional(
                    CONF_USER_IDS,
                    default=(
                        ",".join(data.get(CONF_USER_IDS, []))
                        if isinstance(data.get(CONF_USER_IDS), list)
                        else data.get(CONF_USER_IDS, "")
                    ),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
