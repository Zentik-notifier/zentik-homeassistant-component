# Zentik Notifier (HACS Custom Integration)

Custom Home Assistant integration to create one or multiple notification services backed by the Zentik cloud API.

Each configured instance exposes a `notify` service that sends a JSON payload to the Zentik REST endpoint.

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
service: notify.zentik_notifier_name
data:
	title: "Test Title"
	message: "Hello from Home Assistant"
	data:
	  custom_key: 123
	  nested_value: abc
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
	"userIds": ["user1", "user2"],
	"custom_key": 123,
	"nested_value": "abc"
}
```

	Note: se il campo `data` è un dizionario, le sue coppie chiave/valore vengono aggiunte al livello principale del payload (solo chiavi non già presenti). Se `data` non è un dizionario (stringa, numero, ecc.) viene inviato come chiave singola `data`.

## License

MIT License – see `LICENSE` file.


