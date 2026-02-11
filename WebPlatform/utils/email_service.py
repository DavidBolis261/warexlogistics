"""
Email notification service for Warex Logistics.
Sends order confirmation and status update emails via SMTP.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


# GoDaddy / Microsoft 365 SMTP defaults
DEFAULT_SMTP_HOST = 'smtpout.secureserver.net'
DEFAULT_SMTP_PORT = 465


STATUS_LABELS = {
    'pending': 'Order Placed',
    'allocated': 'Allocated to Driver',
    'in_transit': 'In Transit',
    'delivered': 'Delivered',
    'failed': 'Delivery Failed',
}


def _get_smtp_config(data_manager):
    """Load SMTP settings from the database."""
    host = data_manager.get_setting('smtp_host', DEFAULT_SMTP_HOST)
    port = int(data_manager.get_setting('smtp_port', str(DEFAULT_SMTP_PORT)))
    username = data_manager.get_setting('smtp_username', '')
    password = data_manager.get_setting('smtp_password', '')
    from_email = data_manager.get_setting('smtp_from_email', '')
    enabled = data_manager.get_setting('email_notifications_enabled', 'false').lower() == 'true'
    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'from_email': from_email or username,
        'enabled': enabled,
    }


def is_email_configured(data_manager):
    """Check if email is properly configured."""
    config = _get_smtp_config(data_manager)
    return config['enabled'] and config['username'] and config['password']


def _send_email(config, to_email, subject, html_body):
    """Send an email via SMTP."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config['from_email']
    msg['To'] = to_email

    msg.attach(MIMEText(html_body, 'html'))

    try:
        if config['port'] == 465:
            server = smtplib.SMTP_SSL(config['host'], config['port'], timeout=15)
        else:
            server = smtplib.SMTP(config['host'], config['port'], timeout=15)
            server.starttls()

        server.login(config['username'], config['password'])
        server.sendmail(config['from_email'], to_email, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to_email}: {subject}")
        return {'success': True}
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {'success': False, 'error': str(e)}


def _build_email_template(company_name, tracking_number, content_html, tracking_url=''):
    """Build a styled HTML email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f7; padding: 20px 0;">
<tr>
<td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

<!-- Header -->
<tr>
<td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">{company_name}</h1>
</td>
</tr>

<!-- Body -->
<tr>
<td style="padding: 40px;">
    {content_html}
</td>
</tr>

<!-- Tracking Button -->
{f'''<tr>
<td style="padding: 0 40px 30px; text-align: center;">
    <a href="{tracking_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 6px; font-size: 16px; font-weight: 600;">Track Your Delivery</a>
</td>
</tr>''' if tracking_url else ''}

<!-- Tracking Number -->
<tr>
<td style="padding: 0 40px 30px; text-align: center;">
    <div style="background-color: #f4f4f7; border-radius: 6px; padding: 16px; display: inline-block;">
        <span style="font-size: 12px; color: #8e8ea0; text-transform: uppercase; letter-spacing: 1px;">Tracking Number</span><br>
        <span style="font-size: 20px; font-weight: 700; color: #667eea; letter-spacing: 2px;">{tracking_number}</span>
    </div>
</td>
</tr>

<!-- Footer -->
<tr>
<td style="background-color: #f4f4f7; padding: 20px 40px; text-align: center;">
    <p style="margin: 0; font-size: 12px; color: #8e8ea0;">
        {company_name} &bull; Powered by Warex Logistics
    </p>
</td>
</tr>

</table>
</td>
</tr>
</table>
</body>
</html>"""


def send_order_confirmation(data_manager, order):
    """Send order confirmation email when a new order is created."""
    config = _get_smtp_config(data_manager)
    if not config['enabled'] or not config['username'] or not config['password']:
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

    # Build tracking URL
    domain = data_manager.get_setting('site_domain', '')
    tracking_url = f"https://{domain}?tracking={tracking_number}" if domain else ''

    content_html = f"""
    <h2 style="color: #333; margin: 0 0 10px; font-size: 20px;">Your order is confirmed!</h2>
    <p style="color: #555; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
        Hi {customer}, thank you for your order. We've received your delivery request and it's being processed.
    </p>

    <table width="100%" cellpadding="8" cellspacing="0" style="margin-bottom: 20px;">
        <tr>
            <td style="border-bottom: 1px solid #eee; color: #8e8ea0; font-size: 13px; width: 40%;">Service</td>
            <td style="border-bottom: 1px solid #eee; color: #333; font-size: 15px; font-weight: 600;">{service}</td>
        </tr>
        <tr>
            <td style="border-bottom: 1px solid #eee; color: #8e8ea0; font-size: 13px;">Parcels</td>
            <td style="border-bottom: 1px solid #eee; color: #333; font-size: 15px; font-weight: 600;">{parcels}</td>
        </tr>
        <tr>
            <td style="border-bottom: 1px solid #eee; color: #8e8ea0; font-size: 13px;">Delivering to</td>
            <td style="border-bottom: 1px solid #eee; color: #333; font-size: 15px; font-weight: 600;">{suburb} {postcode}</td>
        </tr>
        <tr>
            <td style="color: #8e8ea0; font-size: 13px;">Status</td>
            <td style="color: #333; font-size: 15px; font-weight: 600;">Order Placed</td>
        </tr>
    </table>

    <p style="color: #8e8ea0; font-size: 13px; line-height: 1.5;">
        You can track your delivery at any time using the tracking number below.
    </p>
    """

    subject = f"Order Confirmed - {tracking_number} | {company_name}"
    html_body = _build_email_template(company_name, tracking_number, content_html, tracking_url)

    return _send_email(config, to_email, subject, html_body)


def send_status_update(data_manager, order, new_status):
    """Send status update email when order status changes."""
    config = _get_smtp_config(data_manager)
    if not config['enabled'] or not config['username'] or not config['password']:
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

    # Different messaging per status
    if new_status == 'allocated':
        heading = "Your delivery has been assigned!"
        message = f"Hi {customer}, great news! A driver has been assigned to your delivery and it will be picked up shortly."
    elif new_status == 'in_transit':
        heading = "Your delivery is on the way!"
        message = f"Hi {customer}, your parcel is now in transit and on its way to you."
    elif new_status == 'delivered':
        heading = "Your delivery is complete!"
        message = f"Hi {customer}, your parcel has been successfully delivered. Thank you for choosing {company_name}!"
    elif new_status == 'failed':
        heading = "Delivery update"
        message = f"Hi {customer}, unfortunately we were unable to complete your delivery. Please contact us for assistance."
    else:
        heading = "Delivery status update"
        message = f"Hi {customer}, your order status has been updated to: {status_label}."

    content_html = f"""
    <h2 style="color: #333; margin: 0 0 10px; font-size: 20px;">{heading}</h2>
    <p style="color: #555; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
        {message}
    </p>

    <div style="background-color: #f4f4f7; border-radius: 6px; padding: 16px 20px; margin-bottom: 20px;">
        <span style="font-size: 12px; color: #8e8ea0; text-transform: uppercase; letter-spacing: 1px;">Current Status</span><br>
        <span style="font-size: 18px; font-weight: 700; color: {'#10b981' if new_status == 'delivered' else '#ef4444' if new_status == 'failed' else '#667eea'};">
            {status_label}
        </span>
    </div>
    """

    subject = f"{status_label} - {tracking_number} | {company_name}"
    html_body = _build_email_template(company_name, tracking_number, content_html, tracking_url)

    return _send_email(config, to_email, subject, html_body)


def test_smtp_connection(data_manager):
    """Test SMTP connection without sending an email."""
    config = _get_smtp_config(data_manager)
    if not config['username'] or not config['password']:
        return {'success': False, 'error': 'SMTP credentials not configured'}

    try:
        if config['port'] == 465:
            server = smtplib.SMTP_SSL(config['host'], config['port'], timeout=10)
        else:
            server = smtplib.SMTP(config['host'], config['port'], timeout=10)
            server.starttls()

        server.login(config['username'], config['password'])
        server.quit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}
