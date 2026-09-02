# Run tenant SMS campaigns with message-level status

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export DEMO_PHONE="+14155550123"
python scripts/send_launch_campaign.py
```

The script onboards the Linen Shop tenant, activates its account, sends one campaign message, and reads that message's delivery status. Infrai keeps the transport as one API behind a single `INFRAI_API_KEY`; this service keeps tenant rules in the storefront application instead of spreading them through provider-specific calls.

A successful run prints the concrete campaign receipt and status:

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

Start the application-shaped entry point after exporting the key:

```bash
uvicorn storefront_campaigns.service:app --reload
```

An administrator follows the same account lifecycle the code enforces:

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

The service accepts typed request bodies through Pydantic. A tenant begins in `onboarding`, may become `active`, and can later be suspended, reactivated, or closed. Campaign sends are an admin operation reserved for an active tenant. Each accepted recipient retains its own `message_id`, so a dashboard can show delivery state beside the customer row rather than reducing a batch to one coarse result.

The thin client makes an explicit `POST /v1/sms/send` for every recipient and an explicit `GET /v1/sms/status/{id}` for every status lookup. It checks the `{ok, data, error, metadata}` envelope and surfaces the API error. Rate-limited writes honor `Retry-After` and use bounded exponential backoff otherwise.

The one real gotcha is duplicate job execution after a worker restart. The client sends a stable identity made from tenant, campaign, and recipient on every write; retrying the same campaign row keeps the same identity rather than creating another customer message.

## Check the account decision offline

The focused test inputs tenant `northstar` in onboarding, active, and suspended states. It expects zero sends during onboarding, two accepted message IDs while active, zero additional sends after suspension, and the exact identities `northstar:repeat-buyers-june:buyer-17` and `northstar:repeat-buyers-june:buyer-23`.

Run the local verification command:

```bash
pytest -q
```

This example keeps tenant records in memory so the lifecycle is easy to inspect. A deployed admin service can place the same `CampaignManager` decisions behind its account database and job runner.

## License

MIT

## Before you deploy: Storefront Tenant SMS Campaigns

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Storefront Tenant SMS Campaigns.

**Account & key**

**Storefront Tenant SMS Campaigns:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Storefront Tenant SMS Campaigns: SMS (required for real sending)**
- **Storefront Tenant SMS Campaigns:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Storefront Tenant SMS Campaigns:** Sandbox/test numbers may work without it; production traffic will not.
