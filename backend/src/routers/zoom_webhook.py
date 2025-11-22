from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import os
import base64
import json
from datetime import datetime
from src.database.connection import get_database

router = APIRouter(prefix="/api/zoom", tags=["Zoom Webhook"])

# ------------------------------------------
# SIGNATURE VERIFICATION
# ------------------------------------------
def verify_signature(secret: str, payload: bytes, timestamp: str, signature: str):
    message = f"v0:{timestamp}:{payload.decode()}"
    computed_hash = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    expected_sig = f"v0={computed_hash}"
    return hmac.compare_digest(expected_sig, signature)


# ------------------------------------------
# MAIN WEBHOOK
# ------------------------------------------
@router.post("/webhook")
async def zoom_webhook(request: Request):

    raw_body = await request.body()
    data = await request.json()

    print("\n==== ZOOM WEBHOOK RECEIVED ====")
    print(raw_body.decode()[:300])

    event = data.get("event")

    # URL validation
    if event == "endpoint.url_validation":
        plain = data["payload"]["plainToken"]
        secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")

        hashed = hmac.new(secret.encode(), plain.encode(), hashlib.sha256).digest()
        encrypted = base64.b64encode(hashed).decode()

        return {"plainToken": plain, "encryptedToken": encrypted}

    # Handle participant join
    if event in ["meeting.participant_joined", "participant.joined"]:
        return await handle_join(data)

    # Handle participant leave
    if event in ["meeting.participant_left", "participant.left"]:
        return await handle_leave(data)

    return {"status": "ignored", "event": event}


# ------------------------------------------
# PARTICIPANT JOIN
# ------------------------------------------
async def handle_join(data: dict):
    obj = data["payload"]["object"]
    p = obj["participant"]

    db = get_database()

    await db.participants.insert_one({
        "meeting_id": obj["id"],
        "user_id": p.get("user_id") or p.get("id"),
        "name": p.get("user_name") or p.get("name"),
        "email": p.get("email"),
        "join_time": datetime.utcnow(),
        "status": "joined"
    })

    print("✔ STORED: participant joined")
    return {"status": "success", "event": "joined"}


# ------------------------------------------
# PARTICIPANT LEFT
# ------------------------------------------
async def handle_leave(data: dict):
    obj = data["payload"]["object"]
    p = obj["participant"]

    db = get_database()

    await db.participants.update_one(
        {"meeting_id": obj["id"], "user_id": p.get("user_id") or p.get("id")},
        {"$set": {"left_time": datetime.utcnow(), "status": "left"}}
    )

    print("✔ UPDATED: participant left")
    return {"status": "success", "event": "left"}


# ------------------------------------------
# TEST ENDPOINT
# ------------------------------------------
@router.get("/webhook/test")
async def test_webhook():
    return {"status": "ok", "message": "Webhook active"}
