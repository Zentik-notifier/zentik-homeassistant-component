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
    CONF_MAGIC_CODE,
    DEFAULT_SERVER_URL,
)


def _normalize_user_ids(raw_users: object) -> list[str]:
    if isinstance(raw_users, str):
        return [u.strip() for u in raw_users.split(",") if u.strip()]
    if isinstance(raw_users, list):
        return [str(u).strip() for u in raw_users if str(u).strip()]
    return []


def _build_unique_combo(*, bucket_id: str | None, magic_code: str | None, user_ids: list[str]) -> str:
    combo_key = ",".join(sorted(user_ids)) if user_ids else "-"
    base = bucket_id if bucket_id else f"magic:{magic_code}"
    return f"{base}|{combo_key}"


class ZentikNotifierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestione del flusso di configurazione per Zentik Notifier."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            bucket_id = (user_input.get(CONF_BUCKET_ID) or "").strip() or None
            access_token = (user_input.get(CONF_ACCESS_TOKEN) or "").strip() or None
            magic_code = (user_input.get(CONF_MAGIC_CODE) or "").strip() or None

            has_token_auth = bool(bucket_id and access_token)
            has_magic_auth = bool(magic_code)
            if not (has_token_auth or has_magic_auth):
                errors["base"] = "auth_required"
            elif has_token_auth and has_magic_auth:
                errors["base"] = "choose_one_auth"

            user_list = _normalize_user_ids(user_input.get(CONF_USER_IDS, ""))

            if not errors:
                unique_combo = _build_unique_combo(
                    bucket_id=bucket_id,
                    magic_code=magic_code,
                    user_ids=user_list,
                )
            await self.async_set_unique_id(unique_combo)
            self._abort_if_unique_id_configured()

                cleaned: dict = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_SERVER_URL: user_input.get(CONF_SERVER_URL, DEFAULT_SERVER_URL),
                    CONF_USER_IDS: user_list,
                }
                if has_magic_auth:
                    cleaned[CONF_MAGIC_CODE] = magic_code
                else:
                    cleaned[CONF_BUCKET_ID] = bucket_id
                    cleaned[CONF_ACCESS_TOKEN] = access_token
                return self.async_create_entry(title=user_input[CONF_NAME], data=cleaned)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Optional(CONF_BUCKET_ID): str,
                vol.Optional(CONF_ACCESS_TOKEN): str,
                vol.Optional(CONF_MAGIC_CODE): str,
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
            bucket_id = (user_input.get(CONF_BUCKET_ID) or "").strip() or None
            access_token = (user_input.get(CONF_ACCESS_TOKEN) or "").strip() or None
            magic_code = (user_input.get(CONF_MAGIC_CODE) or "").strip() or None

            has_token_auth = bool(bucket_id and access_token)
            has_magic_auth = bool(magic_code)
            errors = {}
            if not (has_token_auth or has_magic_auth):
                errors["base"] = "auth_required"
            elif has_token_auth and has_magic_auth:
                errors["base"] = "choose_one_auth"

            user_list = _normalize_user_ids(user_input.get(CONF_USER_IDS, ""))
            candidate_unique = _build_unique_combo(
                bucket_id=bucket_id,
                magic_code=magic_code,
                user_ids=user_list,
            )
            # Manual collision check across entries (covers old entries without unique_id)
            from .const import DOMAIN  # local import
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == self.entry.entry_id:
                    continue
                existing_data = {**entry.data, **entry.options}
                existing_users = _normalize_user_ids(existing_data.get(CONF_USER_IDS, []))
                existing_bucket = existing_data.get(CONF_BUCKET_ID)
                existing_magic = existing_data.get(CONF_MAGIC_CODE)
                existing_combo = _build_unique_combo(
                    bucket_id=existing_bucket,
                    magic_code=existing_magic,
                    user_ids=existing_users,
                )
                if existing_combo == candidate_unique:
                    schema = self._build_schema(user_input)
                    return self.async_show_form(step_id="init", data_schema=schema, errors={"base": "already_configured"})

            if errors:
                schema = self._build_schema(user_input)
                return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

            cleaned: dict = {
                CONF_NAME: user_input.get(CONF_NAME),
                CONF_SERVER_URL: user_input.get(CONF_SERVER_URL, DEFAULT_SERVER_URL),
                CONF_USER_IDS: user_list,
            }
            if has_magic_auth:
                cleaned[CONF_MAGIC_CODE] = magic_code
            else:
                cleaned[CONF_BUCKET_ID] = bucket_id
                cleaned[CONF_ACCESS_TOKEN] = access_token
            return self.async_create_entry(title="", data=cleaned)
        data = {**self.entry.data, **self.entry.options}
        schema = self._build_schema(data)
        return self.async_show_form(step_id="init", data_schema=schema)

    def _build_schema(self, data):
        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=data.get(CONF_NAME)): str,
                vol.Optional(CONF_BUCKET_ID, default=data.get(CONF_BUCKET_ID, "")): str,
                vol.Optional(CONF_ACCESS_TOKEN, default=data.get(CONF_ACCESS_TOKEN, "")): str,
                vol.Optional(CONF_MAGIC_CODE, default=data.get(CONF_MAGIC_CODE, "")): str,
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
