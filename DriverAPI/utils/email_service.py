"""
Email notification service for Warex Logistics.
Sends order confirmation and status update emails via Resend API.
"""

import os
import base64
import io
import logging
import requests as http_requests
from PIL import Image

logger = logging.getLogger(__name__)

# ── Logo helper ───────────────────────────────────────────────────────────────
_LOGO_B64 = None  # module-level cache

def _get_logo_b64():
    """Lazily load and base64-encode the Warex logo for inline email embedding."""
    global _LOGO_B64
    if _LOGO_B64 is not None:
        return _LOGO_B64
    try:
        # static/ sits one directory above utils/
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'warex_logo.png',
        )
        img = Image.open(logo_path).resize((160, 160), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert('RGB').save(buf, format='JPEG', quality=85)
        _LOGO_B64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        _LOGO_B64 = ''
    return _LOGO_B64

RESEND_API_URL = 'https://api.resend.com/emails'

STATUS_LABELS = {
    'pending': 'Order Placed',
    'allocated': 'Allocated to Driver',
    'in_transit': 'In Transit',
    'delivered': 'Delivered',
    'failed': 'Delivery Failed',
}


def _get_email_config(data_manager):
    """Load email settings — env vars take priority over DB settings."""
    # Env vars are the authoritative source in production (Railway).
    # DB settings are the fallback for local / dashboard-configured installs.
    api_key = (
        os.environ.get('RESEND_API_KEY', '').strip()
        or data_manager.get_setting('resend_api_key', '')
    )
    from_email = (
        os.environ.get('EMAIL_FROM_ADDRESS', '').strip()
        or data_manager.get_setting('email_from_address', '')
    )
    db_enabled = data_manager.get_setting('email_notifications_enabled', 'false')
    enabled = str(db_enabled).lower() == 'true'
    return {
        'api_key': api_key,
        'from_email': from_email,
        'enabled': enabled,
    }


def is_email_configured(data_manager):
    """Check if email is properly configured.

    Enabled when:
    - RESEND_API_KEY env var is set (always treated as enabled), OR
    - email_notifications_enabled is 'true' in DB settings
    AND api_key + from_email are present in either source.
    """
    config = _get_email_config(data_manager)
    # If the API key comes from the environment variable, treat notifications
    # as enabled regardless of the DB toggle — the env var being set is
    # sufficient intent.
    env_key_present = bool(os.environ.get('RESEND_API_KEY', '').strip())
    enabled = config['enabled'] or env_key_present
    return enabled and bool(config['api_key']) and bool(config['from_email'])


def _send_email(config, to_email, subject, html_body):
    """Send an email via Resend API."""
    try:
        response = http_requests.post(
            RESEND_API_URL,
            headers={
                'Authorization': f"Bearer {config['api_key']}",
                'Content-Type': 'application/json',
                'Resend-API-Version': '2023-06-1',
            },
            json={
                'from': config['from_email'],
                'to': [to_email],
                'subject': subject,
                'html': html_body,
            },
            timeout=15,
        )

        if response.status_code in (200, 201):
            logger.info(f"Email sent to {to_email}: {subject}")
            return {'success': True}
        else:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get('message', response.text)
            except Exception:
                pass
            logger.error(f"Resend API error ({response.status_code}): {error_msg}")
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {'success': False, 'error': str(e)}


# ── Dark-mode–safe CSS injected into every email <head> ──────────────────────
#
# Strategy (layered, most-to-least capable client):
#   1. <meta name="color-scheme" content="light only"> — tells Apple Mail /
#      iOS Mail / Outlook for Mac NOT to apply any dark-mode transformation.
#   2. :root { color-scheme: light only } — same signal via CSS for clients
#      that read <style> tags (Samsung Mail, Outlook 2019+).
#   3. @media (prefers-color-scheme: dark) overrides — forces explicit light
#      colours on every element for clients that ignore the above but DO
#      support media queries in <style> (older iOS Mail, Thunderbird).
#   4. Inline styles with explicit colour values everywhere — last-resort
#      defence for Gmail, which strips <style> tags entirely.
#
_DARK_MODE_CSS = (
    '<style type="text/css">'
    ':root { color-scheme: light only; }'
    'body { background-color: #f4f4f7 !important; color: #333333 !important; }'
    '@media (prefers-color-scheme: dark) {'
    '  body, .email-wrapper, .email-wrapper table { background-color: #f4f4f7 !important; }'
    '  .email-card { background-color: #ffffff !important; }'
    '  .email-body-cell { background-color: #ffffff !important; color: #333333 !important; }'
    '  .email-tracking-cell { background-color: #ffffff !important; }'
    '  .email-footer-cell { background-color: #f4f4f7 !important; }'
    '  .text-heading { color: #333333 !important; }'
    '  .text-body { color: #555555 !important; }'
    '  .text-muted { color: #8e8ea0 !important; }'
    '  .text-brand { color: #667eea !important; }'
    '  .text-success { color: #10b981 !important; }'
    '  .text-danger { color: #ef4444 !important; }'
    '  .text-white { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }'
    '  .bg-subtle { background-color: #f4f4f7 !important; }'
    '  .info-box { background-color: #dbeafe !important; }'
    '  .info-box p { color: #1e3a8a !important; }'
    '  .btn-track {'
    '    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;'
    '    background-color: #667eea !important;'
    '    color: #ffffff !important;'
    '    -webkit-text-fill-color: #ffffff !important;'
    '    border-color: #667eea !important;'
    '  }'
    '  .table-label { color: #8e8ea0 !important; }'
    '  .table-value { color: #333333 !important; }'
    '  .table-divider { border-bottom-color: #eeeeee !important; }'
    '}'
    '</style>'
)


def _build_email_template(company_name, tracking_number, content_html, tracking_url=''):
    """Build a dark-mode–safe styled HTML email template."""
    tracking_button = ''
    if tracking_url:
        tracking_button = (
            '<tr>'
            '<td class="email-tracking-cell" style="padding: 0 40px 30px; text-align: center; background-color: #ffffff;">'
            f'<a href="{tracking_url}" class="btn-track" '
            'style="display: inline-block; '
            'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'background-color: #667eea; '
            'color: #ffffff !important; '
            '-webkit-text-fill-color: #ffffff; '
            'text-decoration: none; '
            'padding: 14px 40px; '
            'border-radius: 6px; '
            'font-size: 16px; '
            'font-weight: 600; '
            'border: 2px solid #764ba2; '
            'mso-padding-alt: 14px 40px;">'
            'Track Your Delivery'
            '</a>'
            '</td></tr>'
        )

    # Logo in header — load inline base64 so it renders in all email clients
    logo_b64 = _get_logo_b64()
    logo_img = (
        f'<img src="{logo_b64}" alt="{company_name}" '
        'style="width:80px;height:80px;border-radius:12px;display:block;margin:0 auto 12px;" />'
        if logo_b64 else ''
    )

    return (
        '<!DOCTYPE html>'
        '<html lang="en" style="color-scheme: light only;">'
        '<head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        # Prevent Apple Mail / iOS Mail / Outlook for Mac from going dark
        '<meta name="color-scheme" content="light only">'
        '<meta name="supported-color-schemes" content="light">'
        f'{_DARK_MODE_CSS}'
        '</head>'
        '<body style="margin: 0; padding: 0; background-color: #f4f4f7; color: #333333; '
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\">"
        '<table class="email-wrapper" width="100%" cellpadding="0" cellspacing="0" '
        'style="background-color: #f4f4f7; padding: 20px 0;">'
        '<tr><td align="center">'
        # Card container
        '<table class="email-card" width="600" cellpadding="0" cellspacing="0" '
        'style="background-color: #ffffff; border-radius: 8px; '
        'overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">'
        # Header — purple gradient; white text is safe here because the gradient
        # background is a solid brand colour that email clients won't invert.
        '<tr><td class="email-header" '
        'style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
        'background-color: #667eea; '
        'padding: 30px 40px; text-align: center;">'
        f'{logo_img}'
        f'<h1 class="text-white" style="color: #ffffff; -webkit-text-fill-color: #ffffff; margin: 0; font-size: 22px; font-weight: 700;">{company_name}</h1>'
        '</td></tr>'
        # Body
        '<tr><td class="email-body-cell" style="padding: 40px; background-color: #ffffff; color: #333333;">'
        f'{content_html}'
        '</td></tr>'
        # Tracking button (optional)
        f'{tracking_button}'
        # Tracking number badge
        '<tr><td class="email-tracking-cell" style="padding: 0 40px 30px; text-align: center; background-color: #ffffff;">'
        '<div class="bg-subtle" style="background-color: #f4f4f7; border-radius: 6px; padding: 16px; display: inline-block;">'
        '<span class="text-muted" style="font-size: 12px; color: #8e8ea0; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 4px;">Tracking Number</span>'
        f'<span class="text-brand" style="font-size: 20px; font-weight: 700; color: #667eea; letter-spacing: 2px;">{tracking_number}</span>'
        '</div></td></tr>'
        # Footer
        '<tr><td class="email-footer-cell" style="background-color: #f4f4f7; padding: 20px 40px; text-align: center;">'
        f'<p class="text-muted" style="margin: 0; font-size: 12px; color: #8e8ea0;">{company_name} &bull; Powered by Warex Logistics</p>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def send_order_confirmation(data_manager, order):
    """Send order confirmation email when a new order is created."""
    config = _get_email_config(data_manager)
    env_key_present = bool(os.environ.get('RESEND_API_KEY', '').strip())
    effective_enabled = config['enabled'] or env_key_present
    if not effective_enabled or not config['api_key'] or not config['from_email']:
        return {'success': False, 'error': 'Email not configured'}

    to_email = order.get('email', '')
    if not to_email:
        return {'success': False, 'error': 'No customer email'}

    company_name = data_manager.get_setting('company_name', 'Warex Logistics')
    tracking_number = order.get('tracking_number', 'N/A')
    customer = order.get('customer', 'Customer')
    suburb = order.get('suburb', '')
    postcode = order.get('postcode', '')
    service = order.get('service_level', 'standard').capitalize()
    parcels = order.get('parcels', 1)

    domain = data_manager.get_setting('site_domain', '')
    tracking_url = f"https://{domain}?tracking={tracking_number}" if domain else ''

    content_html = (
        '<h2 class="text-heading" style="color: #333333; margin: 0 0 10px; font-size: 20px;">Your order is confirmed!</h2>'
        '<p class="text-body" style="color: #555555; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">'
        f'Hi {customer}, thank you for your order. We have received your delivery request and it is being processed.'
        '</p>'
        '<table width="100%" cellpadding="8" cellspacing="0" style="margin-bottom: 20px;">'
        '<tr><td class="table-label table-divider" style="border-bottom: 1px solid #eeeeee; color: #8e8ea0; font-size: 13px; width: 40%;">Service</td>'
        f'<td class="table-value table-divider" style="border-bottom: 1px solid #eeeeee; color: #333333; font-size: 15px; font-weight: 600;">{service}</td></tr>'
        '<tr><td class="table-label table-divider" style="border-bottom: 1px solid #eeeeee; color: #8e8ea0; font-size: 13px;">Parcels</td>'
        f'<td class="table-value table-divider" style="border-bottom: 1px solid #eeeeee; color: #333333; font-size: 15px; font-weight: 600;">{parcels}</td></tr>'
        '<tr><td class="table-label table-divider" style="border-bottom: 1px solid #eeeeee; color: #8e8ea0; font-size: 13px;">Delivering to</td>'
        f'<td class="table-value table-divider" style="border-bottom: 1px solid #eeeeee; color: #333333; font-size: 15px; font-weight: 600;">{suburb} {postcode}</td></tr>'
        '<tr><td class="table-label" style="color: #8e8ea0; font-size: 13px;">Status</td>'
        '<td class="table-value" style="color: #333333; font-size: 15px; font-weight: 600;">Order Placed</td></tr>'
        '</table>'
        '<div class="info-box" style="background-color: #dbeafe; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-bottom: 20px; border-radius: 4px;">'
        '<p style="color: #1e3a8a; font-size: 13px; line-height: 1.6; margin: 0;">'
        '<strong>Authority to Leave:</strong> The sender has chosen our Authority to Leave delivery service for your parcel. '
        'This means we will leave the parcel in a safe place at the delivery address. '
        '</p>'
        '</div>'
        '<p class="text-muted" style="color: #8e8ea0; font-size: 13px; line-height: 1.5;">'
        'You can track your delivery at any time using the tracking number below.'
        '</p>'
    )

    subject = f"Order Confirmed - {tracking_number} | {company_name}"
    html_body = _build_email_template(company_name, tracking_number, content_html, tracking_url)

    return _send_email(config, to_email, subject, html_body)


def send_status_update(data_manager, order, new_status, proof_photo=None):
    """Send status update email when order status changes.

    ``proof_photo`` is an optional raw base64 string (or data-URL) for the
    delivery photo.  When provided and status is 'delivered', the photo is
    embedded inline in the email so the customer can see where their parcel
    was left.  The timestamp is already stamped onto the photo by the iOS app.
    """
    config = _get_email_config(data_manager)
    # Mirror is_email_configured: env var presence implies enabled
    env_key_present = bool(os.environ.get('RESEND_API_KEY', '').strip())
    effective_enabled = config['enabled'] or env_key_present
    if not effective_enabled or not config['api_key'] or not config['from_email']:
        return {'success': False, 'error': 'Email not configured'}

    to_email = order.get('email', '')
    if not to_email:
        return {'success': False, 'error': 'No customer email'}

    company_name = data_manager.get_setting('company_name', 'Warex Logistics')
    tracking_number = order.get('tracking_number', 'N/A')
    customer = order.get('customer', 'Customer')
    status_label = STATUS_LABELS.get(new_status, new_status.replace('_', ' ').capitalize())

    domain = data_manager.get_setting('site_domain', '')
    tracking_url = f"https://{domain}?tracking={tracking_number}" if domain else ''

    if new_status == 'allocated':
        heading = "Your delivery has been assigned!"
        message = f"Hi {customer}, great news! A driver has been assigned to your delivery and it will be picked up shortly."
    elif new_status == 'in_transit':
        heading = "Your delivery is on the way!"
        message = f"Hi {customer}, your parcel is now in transit and on its way to you."
    elif new_status == 'delivered':
        heading = "Your delivery is complete!"
        message = (
            f"Hi {customer}, your parcel has been successfully delivered. "
            f"Thank you for choosing {company_name}!"
        )
    elif new_status == 'failed':
        heading = "Delivery update"
        message = (
            f"Hi {customer}, unfortunately we were unable to complete your delivery. "
            "Please contact us for assistance."
        )
    else:
        heading = "Delivery status update"
        message = f"Hi {customer}, your order status has been updated to: {status_label}."

    # Status badge colours — explicit inline AND class for dark-mode @media override
    if new_status == 'delivered':
        status_color = '#10b981'
        status_class = 'text-success'
    elif new_status == 'failed':
        status_color = '#ef4444'
        status_class = 'text-danger'
    else:
        status_color = '#667eea'
        status_class = 'text-brand'

    # Build the proof-of-delivery photo block (delivered emails only)
    photo_html = ''
    if new_status == 'delivered' and proof_photo and isinstance(proof_photo, str) and proof_photo.strip():
        # Normalise to a data-URL (raw base64 or data-URL both accepted)
        if proof_photo.startswith('data:'):
            photo_src = proof_photo
        else:
            photo_src = f'data:image/jpeg;base64,{proof_photo}'
        photo_html = (
            '<div style="margin: 20px 0; text-align: center;">'
            '<p class="text-muted" style="font-size: 13px; color: #8e8ea0; margin-bottom: 8px; '
            'text-transform: uppercase; letter-spacing: 1px;">Proof of Delivery</p>'
            f'<img src="{photo_src}" alt="Proof of delivery photo" '
            'style="max-width: 100%; border-radius: 8px; border: 2px solid #10b981;" />'
            '</div>'
        )

    content_html = (
        f'<h2 class="text-heading" style="color: #333333; margin: 0 0 10px; font-size: 20px;">{heading}</h2>'
        f'<p class="text-body" style="color: #555555; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">{message}</p>'
        '<div class="bg-subtle" style="background-color: #f4f4f7; border-radius: 6px; padding: 16px 20px; margin-bottom: 20px;">'
        '<span class="text-muted" style="font-size: 12px; color: #8e8ea0; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 4px;">Current Status</span>'
        f'<span class="{status_class}" style="font-size: 18px; font-weight: 700; color: {status_color};">{status_label}</span>'
        '</div>'
        f'{photo_html}'
    )

    subject = f"{status_label} - {tracking_number} | {company_name}"
    html_body = _build_email_template(company_name, tracking_number, content_html, tracking_url)

    return _send_email(config, to_email, subject, html_body)


def test_email_connection(data_manager):
    """Test Resend API connection by sending a test request."""
    config = _get_email_config(data_manager)
    if not config['api_key']:
        return {'success': False, 'error': 'Resend API key not configured'}

    try:
        # Verify API key by listing domains (lightweight API call)
        response = http_requests.get(
            'https://api.resend.com/domains',
            headers={'Authorization': f"Bearer {config['api_key']}"},
            timeout=10,
        )
        if response.status_code == 200:
            domains = response.json().get('data', [])
            verified = [d['name'] for d in domains if d.get('status') == 'verified']
            if verified:
                return {'success': True, 'domains': verified}
            else:
                return {'success': True, 'warning': 'API key works but no verified domains found. Add your domain in Resend dashboard.'}
        else:
            return {'success': False, 'error': f"API returned {response.status_code}: {response.text}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}
