"""
QR Code generation utilities for shipping labels.
"""

import qrcode
import io
import base64
from PIL import Image


def generate_qr_code(data: str, size: int = 300) -> str:
    """
    Generate a QR code for the given data.

    Args:
        data: The data to encode (e.g., order number)
        size: Size of the QR code in pixels

    Returns:
        Base64 encoded PNG image string for embedding in HTML
    """
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Resize to requested size
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    # Convert to base64 for embedding
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def generate_shipping_label_html(order_data: dict) -> str:
    """
    Generate HTML for a shipping label with QR code.

    Args:
        order_data: Dictionary containing order information

    Returns:
        HTML string for the shipping label
    """
    order_number = order_data.get('order_id', '')
    qr_code_img = generate_qr_code(order_number, size=200)

    html = f"""
    <div style="
        width: 4in;
        height: 6in;
        border: 2px solid black;
        padding: 20px;
        font-family: Arial, sans-serif;
        page-break-after: always;
        background: white;
    ">
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 15px;">
            <h2 style="margin: 0; font-size: 24px;">Sydney Metro Courier</h2>
            <p style="margin: 5px 0; font-size: 12px;">Warex Logistics</p>
        </div>

        <!-- QR Code -->
        <div style="text-align: center; margin: 15px 0;">
            <img src="{qr_code_img}" style="width: 150px; height: 150px;">
            <p style="margin: 5px 0; font-weight: bold; font-size: 16px;">{order_number}</p>
        </div>

        <!-- Delivery Details -->
        <div style="margin-top: 20px; border-top: 2px solid #333; padding-top: 15px;">
            <p style="margin: 5px 0; font-weight: bold; font-size: 14px;">DELIVER TO:</p>
            <p style="margin: 5px 0; font-size: 16px; font-weight: bold;">{order_data.get('customer', '')}</p>
            <p style="margin: 3px 0; font-size: 14px;">{order_data.get('address', '')}</p>
            {f"<p style='margin: 3px 0; font-size: 14px;'>{order_data.get('address2', '')}</p>" if order_data.get('address2') else ''}
            <p style="margin: 3px 0; font-size: 14px;">
                {order_data.get('suburb', '')}, {order_data.get('state', 'NSW')} {order_data.get('postcode', '')}
            </p>
            <p style="margin: 8px 0; font-size: 14px;">
                <strong>Phone:</strong> {order_data.get('phone', '')}
            </p>
        </div>

        <!-- Order Info -->
        <div style="margin-top: 15px; border-top: 1px solid #ccc; padding-top: 10px;">
            <div style="display: flex; justify-content: space-between;">
                <p style="margin: 3px 0; font-size: 12px;">
                    <strong>Service:</strong> {order_data.get('service_level', 'Standard').upper()}
                </p>
                <p style="margin: 3px 0; font-size: 12px;">
                    <strong>Parcels:</strong> {order_data.get('parcels', 1)}
                </p>
            </div>
            {f"<p style='margin: 8px 0; font-size: 11px; background: #fff3cd; padding: 5px; border-radius: 3px;'><strong>Note:</strong> {order_data.get('instructions', '')}</p>" if order_data.get('instructions') else ''}
        </div>
    </div>
    """

    return html
