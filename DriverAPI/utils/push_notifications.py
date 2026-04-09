"""
APNs push notification utility using JWT-based HTTP/2 authentication.

Requires env vars:
  APNS_KEY_ID      — Apple key ID (e.g. 5ZL6GNHZM5)
  APNS_TEAM_ID     — Apple Team ID (e.g. 32GJ539AQ2)
  APNS_BUNDLE_ID   — App bundle ID (e.g. tapaway.warexdriver)
  APNS_PRIVATE_KEY — Full .p8 PEM content (newlines as \\n or real newlines)
"""

import os
import time
import logging

logger = logging.getLogger(__name__)

APNS_KEY_ID     = os.environ.get('APNS_KEY_ID',     '5ZL6GNHZM5')
APNS_TEAM_ID    = os.environ.get('APNS_TEAM_ID',    '32GJ539AQ2')
APNS_BUNDLE_ID  = os.environ.get('APNS_BUNDLE_ID',  'tapaway.warexdriver')
APNS_PRIVATE_KEY = os.environ.get('APNS_PRIVATE_KEY', '')

APNS_HOST = 'https://api.push.apple.com'

# Cache the token to avoid regenerating on every push
_cached_token: str = ''
_token_expiry: int = 0


def _get_apns_token() -> str:
    """Return a valid APNs JWT, regenerating if near expiry (tokens last ~60 min)."""
    global _cached_token, _token_expiry

    now = int(time.time())
    if _cached_token and now < _token_expiry - 120:
        return _cached_token

    try:
        import jwt  # PyJWT
    except ImportError:
        raise RuntimeError("PyJWT is required: pip install PyJWT>=2.8.0")

    private_key = APNS_PRIVATE_KEY
    if not private_key:
        raise ValueError("APNS_PRIVATE_KEY env var is not set")

    # Railway env vars can't contain real newlines — accept \\n as a substitute
    private_key = private_key.replace('\\n', '\n')

    token = jwt.encode(
        {'iss': APNS_TEAM_ID, 'iat': now},
        private_key,
        algorithm='ES256',
        headers={'kid': APNS_KEY_ID},
    )
    _cached_token = token
    _token_expiry = now + 3000  # regenerate after ~50 min
    return token


def send_push_notification(device_token: str, title: str, body: str, data: dict = None) -> bool:
    """Send an APNs alert push notification via HTTP/2.

    Returns True on success, False on any failure (never raises).
    """
    if not device_token:
        return False

    try:
        import httpx
    except ImportError:
        logger.error("[APNs] httpx is required: pip install 'httpx[http2]>=0.25.0'")
        return False

    try:
        apns_token = _get_apns_token()
    except Exception as exc:
        logger.error(f"[APNs] Failed to generate JWT: {exc}")
        return False

    url = f"{APNS_HOST}/3/device/{device_token}"

    payload = {
        "aps": {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
            "badge": 1,
        }
    }
    if data:
        # Merge extra data at the top level (not inside aps)
        payload.update({k: v for k, v in data.items() if k != 'aps'})

    headers = {
        "authorization": f"bearer {apns_token}",
        "apns-topic": APNS_BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }

    try:
        with httpx.Client(http2=True, timeout=10) as client:
            response = client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            logger.info(f"[APNs] ✅ Push sent to ...{device_token[-6:]}")
            return True
        else:
            logger.warning(
                f"[APNs] ❌ Push failed HTTP {response.status_code}: {response.text[:200]}"
            )
            return False

    except Exception as exc:
        logger.error(f"[APNs] ❌ Push error: {exc}")
        return False


def notify_driver_new_run(device_token: str, run_id: str, stop_count: int) -> bool:
    """Notify a driver that a new delivery run has been assigned to them."""
    stops_word = 'stop' if stop_count == 1 else 'stops'
    return send_push_notification(
        device_token,
        title="📦 New Delivery Run",
        body=f"You have been assigned {stop_count} {stops_word} in run {run_id}.",
        data={"run_id": run_id},
    )
