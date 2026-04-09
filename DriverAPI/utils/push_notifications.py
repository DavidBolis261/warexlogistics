"""
APNs push notification utility using JWT-based HTTP/2 authentication.

Requires env vars:
  APNS_KEY_ID      — Apple key ID (e.g. 5ZL6GNHZM5)
  APNS_TEAM_ID     — Apple Team ID (e.g. 32GJ539AQ2)
  APNS_BUNDLE_ID   — App bundle ID (e.g. tapaway.warexdriver)
  APNS_PRIVATE_KEY — .p8 key content: either the bare base64 body OR the full
                     PEM with headers. Newlines may be literal or escaped as \\n.
  APNS_SANDBOX     — set to "true" for debug/dev builds (installed via Xcode).
                     Leave unset or "false" for TestFlight / App Store builds.
"""

import os
import time
import logging

logger = logging.getLogger(__name__)

APNS_KEY_ID      = os.environ.get('APNS_KEY_ID',     '5ZL6GNHZM5')
APNS_TEAM_ID     = os.environ.get('APNS_TEAM_ID',    '32GJ539AQ2')
APNS_BUNDLE_ID   = os.environ.get('APNS_BUNDLE_ID',  'tapaway.warexdriver')
APNS_PRIVATE_KEY = os.environ.get('APNS_PRIVATE_KEY', '')
APNS_SANDBOX     = os.environ.get('APNS_SANDBOX', 'false').lower() == 'true'

APNS_HOST = (
    'https://api.sandbox.push.apple.com'
    if APNS_SANDBOX else
    'https://api.push.apple.com'
)

# Cache the JWT to avoid regenerating on every push (tokens last ~60 min)
_cached_token: str = ''
_token_expiry: int = 0


def _normalise_private_key(raw: str) -> str:
    """Ensure the key is valid PEM, regardless of how it was pasted into Railway."""
    # Un-escape literal \\n sequences used when pasting into Railway env vars
    key = raw.replace('\\n', '\n').strip()

    # If the user pasted only the base64 body (no PEM header), wrap it now
    if '-----' not in key:
        # Fold the base64 body into 64-char lines as PEM requires
        body = key.replace('\n', '').replace(' ', '')
        lines = [body[i:i+64] for i in range(0, len(body), 64)]
        key = '-----BEGIN PRIVATE KEY-----\n' + '\n'.join(lines) + '\n-----END PRIVATE KEY-----'

    return key


def _get_apns_token() -> str:
    """Return a valid APNs JWT, regenerating if near expiry."""
    global _cached_token, _token_expiry

    now = int(time.time())
    if _cached_token and now < _token_expiry - 120:
        return _cached_token

    try:
        import jwt  # PyJWT
    except ImportError:
        raise RuntimeError("PyJWT is required: pip install PyJWT>=2.8.0")

    if not APNS_PRIVATE_KEY:
        raise ValueError("APNS_PRIVATE_KEY env var is not set")

    private_key = _normalise_private_key(APNS_PRIVATE_KEY)

    token = jwt.encode(
        {'iss': APNS_TEAM_ID, 'iat': now},
        private_key,
        algorithm='ES256',
        headers={'kid': APNS_KEY_ID},
    )
    _cached_token = token
    _token_expiry = now + 3000  # regenerate after ~50 min
    env_label = 'sandbox' if APNS_SANDBOX else 'production'
    logger.info(f"[APNs] Generated new JWT for {env_label}")
    return token


def send_push_notification(device_token: str, title: str, body: str, data: dict = None) -> bool:
    """Send an APNs alert push notification via HTTP/2.

    Returns True on success, False on any failure (never raises).
    """
    if not device_token:
        logger.warning("[APNs] send_push_notification called with empty device_token")
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
                f"[APNs] ❌ Push failed HTTP {response.status_code}: {response.text[:300]}"
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
