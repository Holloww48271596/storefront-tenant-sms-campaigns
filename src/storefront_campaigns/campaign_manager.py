from __future__ import annotations

from typing import Any

from .infrai_sms import SmsSendResult
from .models import (
    CampaignReceipt,
    CampaignRequest,
    MessageReceipt,
    MessageStatus,
    TenantCreate,
    TenantState,
    TenantView,
)


class CampaignManager:
    def __init__(self, sms: Any) -> None:
        self._sms = sms
        self._tenants: dict[str, TenantView] = {}

    def onboard(self, request: TenantCreate) -> TenantView:
        if request.tenant_id in self._tenants:
            raise ValueError("tenant already exists")
        tenant = TenantView(**request.model_dump(), state=TenantState.ONBOARDING)
        self._tenants[tenant.tenant_id] = tenant
        return tenant

    def change_state(self, tenant_id: str, target: TenantState) -> TenantView:
        tenant = self._tenant(tenant_id)
        allowed = {
            TenantState.ONBOARDING: {TenantState.ACTIVE, TenantState.CLOSED},
            TenantState.ACTIVE: {TenantState.SUSPENDED, TenantState.CLOSED},
            TenantState.SUSPENDED: {TenantState.ACTIVE, TenantState.CLOSED},
            TenantState.CLOSED: set(),
        }
        if target not in allowed[tenant.state]:
            raise ValueError(f"cannot move tenant from {tenant.state} to {target}")
        updated = tenant.model_copy(update={"state": target})
        self._tenants[tenant_id] = updated
        return updated

    def send_campaign(self, tenant_id: str, campaign: CampaignRequest) -> CampaignReceipt:
        tenant = self._tenant(tenant_id)
        if tenant.state != TenantState.ACTIVE:
            raise PermissionError("only active tenants can send campaigns")

        accepted = []
        for message in campaign.messages:
            identity = f"{tenant_id}:{campaign.campaign_id}:{message.recipient_id}"
            result = self._sms.send(
                to=message.to,
                body=message.body,
                idempotency_key=identity,
            )
            accepted.append(
                MessageReceipt(
                    recipient_id=message.recipient_id,
                    message_id=result.message_id,
                )
            )
        return CampaignReceipt(
            tenant_id=tenant_id,
            campaign_id=campaign.campaign_id,
            accepted=accepted,
        )

    def campaign_status(self, message_ids: list[str]) -> list[MessageStatus]:
        statuses = []
        for message_id in message_ids:
            data = self._sms.status(message_id)
            statuses.append(
                MessageStatus(message_id=message_id, status=str(data["status"]))
            )
        return statuses

    def _tenant(self, tenant_id: str) -> TenantView:
        try:
            return self._tenants[tenant_id]
        except KeyError as exc:
            raise KeyError("tenant not found") from exc
