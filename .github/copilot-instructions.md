# Copilot instructions — Zentik Notifier (Home Assistant)

## Big picture
- This repo is a **Home Assistant custom integration** under `custom_components/zentik_notifier/`.
- Setup is **config-entry based** (UI flow): see `config_flow.py`.
- For each configured entry, the integration registers a **dynamic notify service** under the built-in `notify` domain: `notify.zentik_notifier_<slug>` (see `notify.py`).
- There is also a documented generic service `zentik_notifier.send` (see `__init__.py` + `services.yaml`).

## Runtime flow (important files)
- `config_flow.py`: collects `name`, `bucket_id`, `access_token`, optional `server_url`, optional `user_ids`.
  - Unique id is `bucket_id|<sorted_user_ids>` ("-" if empty) to prevent duplicates.
- `__init__.py`:
  - Declares `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)` (no YAML config).
  - Registers `zentik_notifier.send` and delegates actual sending to `notify.async_send_from_entry`.
  - On `async_setup_entry`, calls `notify.async_register_service(...)` to create `notify.*` services.
- `notify.py`:
  - `async_send_from_entry(...)` builds payload `{bucketId, title, body, ...}` and POSTs to `server_url`.
  - Extra `data` is forwarded: dict keys are flattened into the top-level payload (except `bucketId/title/body`).
- `const.py`: all keys/constants (domain, config keys, defaults).

## Conventions / gotchas
- If you register/rename services, keep `custom_components/zentik_notifier/services.yaml` in sync; HACS validation fails otherwise.
- Keep `custom_components/zentik_notifier/manifest.json` keys sorted: `domain`, `name`, then alphabetical (hassfest requirement).
- Prefer minimal changes consistent with Home Assistant async patterns (no blocking I/O; use `aiohttp`).

## Versioning & releases (HACS)
- HACS is configured to install from a **release ZIP** asset: see `hacs.json` (`zip_release: true`, `filename: zentik_notifier.zip`).
- CI runs on every push to `main`: `.github/workflows/release.yml`.
  - It runs `hassfest` + `hacs/action` validation.
  - It auto-creates a tag `vX.Y.Z` and a GitHub Release (with `zentik_notifier.zip`) **only if** the tag doesn’t already exist.
- To publish a new version: bump `manifest.json` `version`, then merge/push to `main`.

## What to do when changing behavior
- Update translation strings under `custom_components/zentik_notifier/translations/` if you add user-facing fields/errors.
- Keep service schemas consistent between runtime registration (`__init__.py`, `notify.py`) and `services.yaml` docs.
