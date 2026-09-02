from fastapi import FastAPI, HTTPException

from .campaign_manager import CampaignManager
from .infrai_sms import InfraiSmsClient
from .models import (
    CampaignReceipt,
    CampaignRequest,
    MessageStatus,
    TenantCreate,
    TenantStateChange,
    TenantView,
)


app = FastAPI(title="Storefront tenant SMS campaigns")
manager = CampaignManager(InfraiSmsClient())


@app.post("/tenants", response_model=TenantView, status_code=201)
def onboard_tenant(request: TenantCreate) -> TenantView:
    try:
        return manager.onboard(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/tenants/{tenant_id}/state", response_model=TenantView)
def change_tenant_state(tenant_id: str, request: TenantStateChange) -> TenantView:
    try:
        return manager.change_state(tenant_id, request.state)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/tenants/{tenant_id}/campaigns", response_model=CampaignReceipt)
def send_campaign(tenant_id: str, request: CampaignRequest) -> CampaignReceipt:
    try:
        return manager.send_campaign(tenant_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/campaigns/status", response_model=list[MessageStatus])
def campaign_status(message_id: list[str]) -> list[MessageStatus]:
    return manager.campaign_status(message_id)

