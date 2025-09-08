# Zentik Notifier (HACS Custom Integration)

Custom Home Assistant integration to create one or multiple notification services backed by the Zentik cloud API.

Each configured instance exposes a `notify` service that sends a JSON payload to the Zentik REST endpoint.

## Features

- UI configuration (Config Flow)
- Multiple instances (different buckets / tokens)
- Options Flow to edit parameters after creation
- Sensible default for `server_url`
- English & Italian translations

## Per‑Notifier Parameters

| Field | Description | Required | Default |
|-------|-------------|----------|---------|
| name | Friendly name shown in HA | Yes | — |
| bucket_id | Zentik Bucket ID | Yes | — |
| access_token | Zentik Access Token | Yes | — |
| server_url | Zentik API endpoint | No | https://notifier-api.zentik.app/api/v1/messages |
| user_ids | Target user IDs (comma separated in UI) | No | — |

## Installation (HACS)

1. Open HACS → Integrations → Menu (⋮) → Custom repositories
2. Add repository URL: `https://github.com/Zentik-notifier/zentik-homeassistant-component` with category `Integration`
3. Install "Zentik Notifier"
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → search for "Zentik Notifier"

### Manual Installation (Alternative)
Copy the `custom_components/zentik_notifier` folder into your Home Assistant `config/custom_components` directory and restart.

## Configuration

During setup you will be asked for:
- Friendly name
- Bucket ID
- Access Token
- (Optional) Server URL

You can later adjust them via the integration Options dialog.

## Usage

Call the created notify service from an automation or Developer Tools → Services. Example:

```yaml
service: notify.zentik_notifier
data:
	title: "Test Title"
	message: "Hello from Home Assistant"
```

If you add multiple instances, service names may be suffixed (e.g. `notify.zentik_notifier_bucket123`).

## Payload Sent

HTTP Headers:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

JSON Body:
```json
{
	"bucketId": "<bucket_id>",
	"title": "...",
	"message": "...",
	"userIds": ["user1", "user2"]
}
```

Change log:

## Troubleshooting

| Issue | Check |
|-------|-------|
| No service appears | Restart HA and clear browser cache; confirm folder path is correct. |
| 4xx / 5xx errors in logs | Validate token & bucket; confirm endpoint reachable. |
| Connection errors | Verify network / DNS and HTTPS accessibility. |

## Security Notes
Access token is stored in Home Assistant's storage area. Treat it as a secret. Rotate tokens periodically if supported by Zentik.

## Development

1. Fork & clone repo
2. Place inside a HA dev environment under `config/custom_components/`
3. Bump version in `manifest.json` before release

Recommended extras (not yet included): tests (`pytest` with `pytest-homeassistant-custom-component`), CI workflow, code style (ruff / black), remote credential validation.

## Roadmap / Ideas
- Remote validation of credentials in Config Flow
- Retry / backoff + error surfacing in UI
- Rich notification fields (priority, tags)
- Optional encryption

## License

MIT License – see `LICENSE` file.


