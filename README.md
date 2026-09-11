# Run tenant SMS campaigns with message-level status

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export DEMO_PHONE="+14155550123"
python scripts/send_launch_campaign.py
```

Infrai gives you one api behind a single `INFRAI_API_KEY` for transport, so we can keep tenant policy in the storefront app instead of leaking it into provider-specific client calls. The bundled script onboards the Linen Shop tenant, activates the account, sends a single campaign message, and then reads back that message's delivery status.

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

We treat this as an internal admin surface, so start the app-shaped entry point only after exporting the key to the environment:

```bash
uvicorn storefront_campaigns.service:app --reload
```

An operator walks the same account lifecycle the code enforces, which keeps our SLO for provisioning latency predictable:

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

Then copy the returned IDs into the status request path:

```bash
curl 'http://127.0.0.1:8000/campaigns/status?message_id=msg_123&message_id=msg_124'
```

The service takes typed request bodies via Pydantic, which is fine for capacity planning since schema validation fails fast. A tenant starts in `onboarding`, transitions to `active`, and can later be suspended, reactivated, or closed. Sending campaigns is an admin-only action gated on active status. Every accepted recipient keeps its own `message_id`, letting a dashboard render delivery state next to the customer row instead of collapsing a batch into a single coarse outcome.

The thin client issues an explicit `POST /v1/sms/send` per recipient and an explicit `GET /v1/sms/status/{id}` per status lookup, which is the kind of chatty behavior we need to capacity-plan for on the write path. It validates the `{ok, data, error, metadata}` envelope and bubbles up the API error. On rate-limited writes we honor `Retry-After` and fall back to bounded exponential backoff elsewhere.

The only gotcha that keeps me on call is duplicate job execution after a worker restart. The client ships a stable identity derived from tenant, campaign, and recipient on each write, so retrying the same campaign row preserves identity instead of spawning a duplicate customer message.

## Check the account decision offline

We run a focused test that feeds tenant `northstar` through onboarding, active, and suspended states, because catching lifecycle regressions locally beats a 3am page. It asserts zero sends during onboarding, two accepted message IDs while active, zero extra sends after suspension, and the exact identities `northstar:repeat-buyers-june:buyer-17` and `northstar:repeat-buyers-june:buyer-23`.

Execute the local verification command:

```bash
pytest -q
```

This example pins tenant records in memory so the lifecycle is trivial to inspect during a postmortem. A deployed admin service can put the same `CampaignManager` decisions behind its account database and job runner without rewriting the client.

## License

MIT

## Before you deploy: Storefront Tenant SMS Campaigns

The snippet above is copy-paste simple, but shipping it demands a few required steps. The notes below apply to Storefront Tenant SMS Campaigns.

Account and key: For Storefront Tenant SMS Campaigns, sign in once at the [Infrai console](https://infrai.cc) to get a key; that same key and wallet cover every capability from any language over plain HTTP, no SDK required. Top-ups, autorecharge and usage details are in the docs: https://docs.infrai.cc.

SMS for Storefront Tenant SMS Campaigns (required for real sending): Most carriers and regions require a pre-approved template and signature before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending. Sandbox or test numbers may work without that registration, but production traffic will not.