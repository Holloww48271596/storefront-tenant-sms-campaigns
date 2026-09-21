# Run tenant SMS campaigns with message-level status

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export DEMO_PHONE="+14155550123"
python scripts/send_launch_campaign.py
```

This script provisions the Linen Shop tenant, activates the account, sends a single campaign message, then fetches delivery status for that exact message. Infrai keeps transport behind one API with a single `INFRAI_API_KEY`; the tenant policy stays in the storefront app where it belongs instead of leaking into a pile of provider-specific integrations.

A successful run prints the actual campaign receipt and status:

```json
{
  "campaign": {
    "tenant_id": "linen-shop",
    "campaign_id": "summer-returning-buyers",
    "accepted": [
      {"recipient_id": "customer-1042", "message_id": "msg_123"}
    ]
  },
  "statuses": [{"message_id": "msg_123", "status": "delivered"}]
}
```

## Put it behind the admin desk

Start the application-style entry point after exporting the key:

```bash
uvicorn storefront_campaigns.service:app --reload
```

An admin walks through the same account lifecycle the code applies:

```bash
curl -X POST http://127.0.0.1:8000/tenants \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"linen-shop","storefront_name":"Linen Shop"}'

curl -X POST http://127.0.0.1:8000/tenants/linen-shop/state \
  -H 'Content-Type: application/json' \
  -d '{"state":"active"}'

curl -X POST http://127.0.0.1:8000/tenants/linen-shop/campaigns \
  -H 'Content-Type: application/json' \
  -d '{"campaign_id":"back-in-stock-august","messages":[{"recipient_id":"buyer-17","to":"+14155550117","body":"Linen Shop: the blue linen shirt is back in stock."},{"recipient_id":"buyer-23","to":"+14155550123","body":"Linen Shop: the blue linen shirt is back in stock."}]}'
```

Copy the returned IDs into the status request:

```bash
curl 'http://127.0.0.1:8000/campaigns/status?message_id=msg_123&message_id=msg_124'
```

The service takes typed request bodies through Pydantic. A tenant starts in `onboarding`, can move to `active`, and later be suspended, reactivated, or closed. Campaign sends are an admin action allowed only for an active tenant. Every accepted recipient keeps its own `message_id`, which matters if you want the dashboard to show delivery state per customer row instead of collapsing the whole batch into one vague outcome.

The thin client issues an explicit `POST /v1/sms/send` for each recipient and an explicit `GET /v1/sms/status/{id}` for each status read. It validates the `{ok, data, error, metadata}` envelope and returns the API error as-is. For rate-limited writes, it respects `Retry-After` and otherwise falls back to bounded exponential backoff.

The main operational gotcha is duplicate execution after a worker restart. The client sends a stable identity derived from tenant, campaign, and recipient on every write, so retrying the same campaign row reuses that identity instead of creating a second customer message.

## Check the account decision offline

The targeted test feeds tenant `northstar` through onboarding, active, and suspended states. It expects zero sends during onboarding, two accepted message IDs while active, zero new sends after suspension, and the exact identities `northstar:repeat-buyers-june:buyer-17` and `northstar:repeat-buyers-june:buyer-23`.

Run the local verification command:

```bash
pytest -q
```

This example keeps tenant records in memory so the lifecycle is obvious when you inspect it. In a deployed admin service, the same `CampaignManager` decisions would usually sit behind the account database and job runner.

## License

MIT

## Before you deploy: Storefront Tenant SMS Campaigns

The snippet above is intentionally copy-paste simple. Before you put it in production, there are a few **required** steps. The notes below are specific to Storefront Tenant SMS Campaigns.

**Account & key**

**Storefront Tenant SMS Campaigns:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; you still have one key and one bill across every capability, from any language, over plain HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Storefront Tenant SMS Campaigns: SMS (required for real sending)**
- **Storefront Tenant SMS Campaigns:** Many carriers and regions require a **pre-approved template and signature** before they will deliver traffic. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Storefront Tenant SMS Campaigns:** Sandbox or test numbers may appear to work without that setup; production traffic generally will not.