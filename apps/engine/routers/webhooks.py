import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from svix.webhooks import Webhook, WebhookVerificationError

from db.client import get_supabase

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_SUPPORTED_EVENTS = {"user.created", "user.updated"}


def _get_primary_email(data: dict[str, Any]) -> str:
    addresses: list[dict[str, Any]] = data.get("email_addresses", [])
    primary_id: str | None = data.get("primary_email_address_id")
    for addr in addresses:
        if addr.get("id") == primary_id:
            return addr["email_address"]
    # Fallback: first address in the list
    if addresses:
        return addresses[0]["email_address"]
    raise ValueError(f"No email address found in Clerk payload for user {data.get('id')}")


@router.post("/clerk", status_code=200)
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
) -> dict[str, str]:
    secret = os.environ["CLERK_SECRET_KEY"]
    body = await request.body()

    try:
        wh = Webhook(secret)
        payload: dict[str, Any] = wh.verify(  # type: ignore[assignment]
            body,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type: str = payload.get("type", "")
    if event_type not in _SUPPORTED_EVENTS:
        return {"status": "ignored"}

    data: dict[str, Any] = payload["data"]
    user_id: str = data["id"]
    email = _get_primary_email(data)

    supabase = get_supabase()

    if event_type == "user.created":
        supabase.table("users").upsert(
            {"id": user_id, "email": email, "plan": "free"},
            on_conflict="id",
        ).execute()

    elif event_type == "user.updated":
        supabase.table("users").update({"email": email}).eq("id", user_id).execute()

    return {"status": "ok"}
