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
            raw_users = user_input.get(CONF_USER_IDS, "")
            if isinstance(raw_users, str):
                user_list = [u.strip() for u in raw_users.split(",") if u.strip()]
            else:
                user_list = raw_users or []
            # Unique combo bucket + sorted user ids (use '-' sentinel for empty)
            combo_key = ",".join(sorted(user_list)) if user_list else "-"
            unique_combo = f"{user_input[CONF_BUCKET_ID]}|{combo_key}"
            await self.async_set_unique_id(unique_combo)
            self._abort_if_unique_id_configured()
            user_input[CONF_USER_IDS] = user_list
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
            raw_users = user_input.get(CONF_USER_IDS, "")
            if isinstance(raw_users, str):
                user_list = [u.strip() for u in raw_users.split(",") if u.strip()]
            else:
                user_list = raw_users or []
            combo_key = ",".join(sorted(user_list)) if user_list else "-"
            candidate_unique = f"{user_input[CONF_BUCKET_ID]}|{combo_key}"
            # Manual collision check across entries (covers old entries without unique_id)
            from .const import DOMAIN  # local import
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == self.entry.entry_id:
                    continue
                existing_users = entry.data.get(CONF_USER_IDS, [])
                if isinstance(existing_users, str):
                    existing_users = [u.strip() for u in existing_users.split(",") if u.strip()]
                existing_key = ",".join(sorted(existing_users)) if existing_users else "-"
                existing_combo = f"{entry.data.get(CONF_BUCKET_ID)}|{existing_key}"
                if existing_combo == candidate_unique:
                    schema = self._build_schema(user_input)
                    return self.async_show_form(step_id="init", data_schema=schema, errors={"base": "already_configured"})
            user_input[CONF_USER_IDS] = user_list
            return self.async_create_entry(title="", data=user_input)
        data = {**self.entry.data, **self.entry.options}
        schema = self._build_schema(data)
        return self.async_show_form(step_id="init", data_schema=schema)

    def _build_schema(self, data):
        return vol.Schema(
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
