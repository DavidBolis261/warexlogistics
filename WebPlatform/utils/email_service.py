"""
Email notification service for Warex Logistics.
Sends order confirmation and status update emails via Resend API.
"""

import os
import logging
import requests as http_requests

logger = logging.getLogger(__name__)

RESEND_API_URL = 'https://api.resend.com/emails'

STATUS_LABELS = {
    'pending': 'Order Placed',
    'allocated': 'Allocated to Driver',
    'in_transit': 'In Transit',
    'delivered': 'Delivered',
    'failed': 'Delivery Failed',
}


def _get_email_config(data_manager):
    """Load email settings from environment and database."""
    api_key = os.environ.get('RESEND_API_KEY', '') or data_manager.get_setting('resend_api_key', '')
    from_email = data_manager.get_setting('email_from_address', '')
    enabled = data_manager.get_setting('email_notifications_enabled', 'false').lower() == 'true'
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


def _build_email_template(company_name, tracking_number, content_html, tracking_url=''):
    """Build a styled HTML email template."""
    tracking_button = ''
    if tracking_url:
        tracking_button = (
            '<tr>'
            '<td style="padding: 0 40px 30px; text-align: center;">'
            f'<a href="{tracking_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">'
            'Track Your Delivery</a>'
            '</td></tr>'
        )

    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"></head>'
        '<body style="margin: 0; padding: 0; background-color: #f4f4f7; '
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\">"
        '<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f7; padding: 20px 0;">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; '
        'overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">'
        # Header
        '<tr><td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; text-align: center;">'
        f'<h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">{company_name}</h1>'
        '</td></tr>'
        # Body
        f'<tr><td style="padding: 40px;">{content_html}</td></tr>'
        # Tracking Button
        f'{tracking_button}'
        # Tracking Number
        '<tr><td style="padding: 0 40px 30px; text-align: center;">'
        '<div style="background-color: #f4f4f7; border-radius: 6px; padding: 16px; display: inline-block;">'
        '<span style="font-size: 12px; color: #8e8ea0; text-transform: uppercase; letter-spacing: 1px;">Tracking Number</span><br>'
        f'<span style="font-size: 20px; font-weight: 700; color: #667eea; letter-spacing: 2px;">{tracking_number}</span>'
        '</div></td></tr>'
        # Driver Safety Section
        '<tr><td style="padding: 0 40px 20px;">'
        '<div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px 20px; border-radius: 4px;">'
        '<p style="margin: 0 0 8px; font-size: 14px; font-weight: 700; color: #92400e;">🐕 Driver safety on delivery</p>'
        '<p style="margin: 0; font-size: 13px; line-height: 1.6; color: #78350f;">'
        'We love dogs. But your dog might not love our drivers.<br>'
        'Please make sure our drivers have safe access to your delivery location.'
        '</p></div></td></tr>'
        # Contact Section
        '<tr><td style="padding: 0 40px 30px;">'
        '<div style="background-color: #e0e7ff; border-left: 4px solid #667eea; padding: 16px 20px; border-radius: 4px;">'
        '<p style="margin: 0 0 8px; font-size: 14px; font-weight: 700; color: #3730a3;">💬 Just ask us!</p>'
        '<p style="margin: 0; font-size: 13px; line-height: 1.6; color: #312e81;">'
        'Want to find out more about the broad range of services we can offer you or your business?<br>'
        'Just ask our knowledgeable team on <a href="mailto:admin@warexlogistics.com.au" style="color: #667eea; text-decoration: none; font-weight: 600;">info@warexlogistics.com.au</a>.'
        '</p></div></td></tr>'
        # Footer
        '<tr><td style="background-color: #f4f4f7; padding: 20px 40px; text-align: center;">'
        f'<p style="margin: 0; font-size: 12px; color: #8e8ea0;">{company_name} &bull; Powered by Warex Logistics</p>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def send_order_confirmation(data_manager, order):
    """Send order confirmation email when a new order is created."""
    config = _get_email_config(data_manager)
    if not config['enabled'] or not config['api_key'] or not config['from_email']:
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
        '<h2 style="color: #333; margin: 0 0 10px; font-size: 20px;">Your order is confirmed!</h2>'
        '<p style="color: #555; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">'
        f'Hi {customer}, thank you for your order. We have received your delivery request and it is being processed.'
        '</p>'
        '<table width="100%" cellpadding="8" cellspacing="0" style="margin-bottom: 20px;">'
        '<tr><td style="border-bottom: 1px solid #eee; color: #8e8ea0; font-size: 13px; width: 40%;">Service</td>'
        f'<td style="border-bottom: 1px solid #eee; color: #333; font-size: 15px; font-weight: 600;">{service}</td></tr>'
        '<tr><td style="border-bottom: 1px solid #eee; color: #8e8ea0; font-size: 13px;">Parcels</td>'
        f'<td style="border-bottom: 1px solid #eee; color: #333; font-size: 15px; font-weight: 600;">{parcels}</td></tr>'
        '<tr><td style="border-bottom: 1px solid #eee; color: #8e8ea0; font-size: 13px;">Delivering to</td>'
        f'<td style="border-bottom: 1px solid #eee; color: #333; font-size: 15px; font-weight: 600;">{suburb} {postcode}</td></tr>'
        '<tr><td style="color: #8e8ea0; font-size: 13px;">Status</td>'
        '<td style="color: #333; font-size: 15px; font-weight: 600;">Order Placed</td></tr>'
        '</table>'
        '<div style="background-color: #f0f9ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-bottom: 20px; border-radius: 4px;">'
        '<p style="color: #1e40af; font-size: 13px; line-height: 1.6; margin: 0;">'
        '<strong>Authority to Leave:</strong> The sender has chosen our Authority to Leave delivery service for your parcel. '
        'This means we will leave the parcel in a safe place at the delivery address. '
        '</p>'
        '</div>'
        '<p style="color: #8e8ea0; font-size: 13px; line-height: 1.5;">'
        'You can track your delivery at any time using the tracking number below.'
        '</p>'
    )

    subject = f"Order Confirmed - {tracking_number} | {company_name}"
    html_body = _build_email_template(company_name, tracking_number, content_html, tracking_url)

    return _send_email(config, to_email, subject, html_body)


def send_status_update(data_manager, order, new_status):
    """Send status update email when order status changes."""
    config = _get_email_config(data_manager)
    if not config['enabled'] or not config['api_key'] or not config['from_email']:
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

    if new_status == 'delivered':
        status_color = '#10b981'
    elif new_status == 'failed':
        status_color = '#ef4444'
    else:
        status_color = '#667eea'

    content_html = (
        f'<h2 style="color: #333; margin: 0 0 10px; font-size: 20px;">{heading}</h2>'
        f'<p style="color: #555; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">{message}</p>'
        '<div style="background-color: #f4f4f7; border-radius: 6px; padding: 16px 20px; margin-bottom: 20px;">'
        '<span style="font-size: 12px; color: #8e8ea0; text-transform: uppercase; letter-spacing: 1px;">Current Status</span><br>'
        f'<span style="font-size: 18px; font-weight: 700; color: {status_color};">{status_label}</span>'
        '</div>'
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
