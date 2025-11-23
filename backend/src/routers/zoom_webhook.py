from fastapi import APIRouter, Request, Header, HTTPException
import hmac, hashlib, base64, os, json
from datetime import datetime
from src.database.connection import get_database

router = APIRouter(prefix="/api/zoom", tags=["Zoom Webhook"])


def compute_signature(secret: str, timestamp: str, body: bytes):
    message = f"v0:{timestamp}:{body.decode()}"
    hash_ = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"v0={hash_}"


@router.post("/events")
async def zoom_events(
    request: Request,
    zoom_signature: str = Header(None, alias="x-zoom-signature"),
    zoom_timestamp: str = Header(None, alias="x-zoom-request-timestamp")
):

    raw = await request.body()
    data = json.loads(raw.decode())

    event = data.get("event")
    payload = data.get("payload", {})
    obj = payload.get("object", {})
    participant = obj.get("participant", {})

    db = get_database()

    # URL VALIDATION
    if event == "endpoint.url_validation":
        plain = payload["plainToken"]
        secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")
        hashed = hmac.new(secret.encode(), plain.encode(), hashlib.sha256).digest()
        encrypted = base64.b64encode(hashed).decode()
        return {"plainToken": plain, "encryptedToken": encrypted}

    # SIGNATURE VALIDATION
    if zoom_signature:
        secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")
        expected = compute_signature(secret, zoom_timestamp, raw)
        if not hmac.compare_digest(expected, zoom_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # COMMON MAPPED FIELDS (base document)
    base_doc = {
        "zoom_meeting_id": obj.get("id"),
        "meeting_topic": obj.get("topic"),
        "meeting_uuid": obj.get("uuid"),

        "user_id": participant.get("user_id") or participant.get("id"),
        "user_name": participant.get("user_name") or participant.get("name"),
        "email": participant.get("email"),

        "participant_user_id": participant.get("participant_user_id"),
        "participant_uuid": participant.get("participant_uuid"),

        "public_ip": participant.get("ip_address"),
        "private_ip": participant.get("private_ip_address"),

        "raw_participant_data": participant,  # Store everything

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # -----------------------------
    #  EVENT: PARTICIPANT JOINED
    # -----------------------------
    if event == "meeting.participant_joined":

        doc = {
            **base_doc,
            "status": "joined",
            "join_time": participant.get("join_time"),
            "event": "joined"
        }

        await db.participation.insert_one(doc)
        print("✔ JOIN DATA STORED:", doc)
        return {"status": "ok", "event": "joined"}


    # -----------------------------
    #  EVENT: PARTICIPANT LEFT
    # -----------------------------
    if event == "meeting.participant_left":

        doc = {
            **base_doc,
            "status": "left",
            "leave_time": participant.get("leave_time"),
            "leave_reason": participant.get("leave_reason"),
            "event": "left"
        }

        await db.participation.insert_one(doc)
        print("✔ LEAVE DATA STORED:", doc)
        return {"status": "ok", "event": "left"}


    # -----------------------------
    #  EVENT: MEETING ENDED
    # -----------------------------
    if event == "meeting.ended":

        doc = {
            "zoom_meeting_id": obj.get("id"),
            "meeting_topic": obj.get("topic"),
            "meeting_uuid": obj.get("uuid"),
            "duration": obj.get("duration"),
            "timezone": obj.get("timezone"),
            "event": "meeting_ended",
            "created_at": datetime.utcnow(),
        }

        await db.participation.insert_one(doc)
        print("✔ MEETING ENDED STORED:", doc)
        return {"status": "ok", "event": "meeting_ended"}

    return {"status": "ignored", "event": event}
