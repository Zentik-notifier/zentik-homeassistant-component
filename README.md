# Zentik Notifier (HACS Custom Integration)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Zentik-notifier&repository=zentik-homeassistant-component&category=integration)

Custom Home Assistant integration to create one or multiple notification services backed by the Zentik cloud API.

Each configured instance exposes a `notify` service that sends a JSON payload to the Zentik REST endpoint.

## Per‑Notifier Parameters

| Field | Description | Required | Default |
|-------|-------------|----------|---------|
| name | Friendly name shown in HA | Yes | — |
| bucket_id | Zentik Bucket ID | One of | — |
| access_token | Zentik Access Token | One of | — |
| magic_code | Zentik Magic Code | One of | — |
| server_url | Zentik API endpoint | No | https://notifier-api.zentik.app/messages |
| user_ids | Target user IDs (comma separated in UI) | No | — |

Notes:
- Authentication must be provided as **either** `bucket_id` + `access_token` **or** `magic_code`.

## Installation (HACS)

Fastest way:
- Click the badge at the top (My Home Assistant) and add the repository to HACS.
- Then install **Zentik Notifier** from HACS → Integrations.

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
- Bucket ID + Access Token (optional)
- Magic Code (optional)
- (Optional) Server URL

You can later adjust them via the integration Options dialog.

## Usage

Call the created notify service from an automation or Developer Tools → Services. Example:

```yaml
service: notify.zentik_notifier_name
data:
	title: "Test Title"
	message: "Hello from Home Assistant"
	subtitle: ",,,"
	collapseId: "..."
	groupId: "..."
	imageUrl: "..."
	addMarkAsReadAction: true
	addDeleteAction: true
	actions:
		- type: NAVIGATE
			value: "..."
			icon: house
			title: Open homeassistant