"""Generate Warex Logistics Partner API documentation as a styled PDF."""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

OUTPUT = "/Users/davidbolis/Desktop/Warex_Partner_API_Docs.pdf"

# ── Colours ──────────────────────────────────────────────────────────────────
BRAND      = colors.HexColor("#F59E0B")
DARK       = colors.HexColor("#111827")
MID        = colors.HexColor("#374151")
LIGHT      = colors.HexColor("#6B7280")
CODE_BG    = colors.HexColor("#1E1E2E")
CODE_FG    = colors.HexColor("#CDD6F4")
GREEN      = colors.HexColor("#10B981")
BLUE       = colors.HexColor("#3B82F6")
RED        = colors.HexColor("#EF4444")
BORDER     = colors.HexColor("#E5E7EB")
ROW_ALT    = colors.HexColor("#F9FAFB")
ROW_HEAD   = colors.HexColor("#F3F4F6")

PAGE_W = 170*mm  # usable width (A4 210 - 20 margins each side)

# ── Paragraph styles ──────────────────────────────────────────────────────────
def sty(name, **kw):
    defaults = dict(fontName="Helvetica", fontSize=10, textColor=MID,
                    leading=15, spaceAfter=4, spaceBefore=0)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

H1    = sty("H1",  fontSize=24, textColor=DARK, fontName="Helvetica-Bold", leading=28, spaceAfter=2)
H2    = sty("H2",  fontSize=15, textColor=DARK, fontName="Helvetica-Bold", leading=20, spaceAfter=4, spaceBefore=14)
H3    = sty("H3",  fontSize=11, textColor=MID,  fontName="Helvetica-Bold", leading=15, spaceAfter=4, spaceBefore=10)
BODY  = sty("BODY")
SMALL = sty("SMALL", fontSize=9, textColor=LIGHT, leading=13)
CODE  = sty("CODE",  fontSize=8, textColor=CODE_FG, fontName="Courier", leading=12,
            leftIndent=0, rightIndent=0)
TH    = sty("TH",  fontSize=9,  textColor=DARK, fontName="Helvetica-Bold", leading=12)
TD    = sty("TD",  fontSize=9,  textColor=MID,  fontName="Helvetica",      leading=12)
TDC   = sty("TDC", fontSize=9,  textColor=MID,  fontName="Courier",        leading=12)
WHITE_BOLD = sty("WB", fontSize=9,  textColor=colors.white, fontName="Helvetica-Bold", leading=12)
WHITE_MONO = sty("WM", fontSize=10, textColor=colors.white, fontName="Courier-Bold",   leading=14)
WHITE_SM   = sty("WS", fontSize=8,  textColor=colors.HexColor("#9CA3AF"), fontName="Helvetica", leading=11)


def code_block(lines):
    rows = [[Paragraph(
        line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace(" ", "&nbsp;"),
        CODE
    )] for line in lines]
    if not rows:
        rows = [[Paragraph("", CODE)]]
    t = Table(rows, colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), CODE_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
    ]))
    return t


def endpoint_pill(method, path, description):
    colour = {"POST": GREEN, "GET": BLUE, "PUT": BRAND, "DELETE": RED}.get(method, LIGHT)
    badge  = Table([[Paragraph(method, WHITE_BOLD)]], colWidths=[16*mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colour),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    path_block = Table(
        [[Paragraph(path, WHITE_MONO)],
         [Paragraph(description, WHITE_SM)]],
        colWidths=[148*mm]
    )
    path_block.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    row = Table([[badge, path_block]], colWidths=[20*mm, 150*mm])
    row.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return row


def data_table(header_row, data_rows, col_widths):
    header = [Paragraph(h, TH) for h in header_row]
    rows   = [[Paragraph(str(cell), TDC if i == 0 else TD) for i, cell in enumerate(row)]
              for row in data_rows]
    table_data = [header] + rows
    t = Table(table_data, colWidths=col_widths)
    style = [
        ("BACKGROUND",    (0, 0), (-1,  0), ROW_HEAD),
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    t.setStyle(TableStyle(style))
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=2)


def sp(h=4):
    return Spacer(1, h*mm)


# ── Build ────────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm,  bottomMargin=20*mm,
        title="Warex Logistics — Partner API",
        author="Warex Logistics",
    )
    s = []

    # ── Header banner ─────────────────────────────────────────────────────────
    banner = Table([[
        Paragraph("Warex Logistics", sty("bt", fontSize=22, textColor=colors.white,
                  fontName="Helvetica-Bold", leading=26)),
        Paragraph("Partner API Documentation", sty("bs", fontSize=13, textColor=BRAND,
                  fontName="Helvetica-Bold", leading=18)),
    ]], colWidths=[80*mm, 90*mm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    s.append(banner)
    s.append(sp(3))
    s.append(Paragraph(
        "Base URL: <font name='Courier'>https://eloquent-cooperation-production-12c5.up.railway.app</font> &nbsp;·&nbsp; "
        "Version: v1 &nbsp;·&nbsp; Format: JSON",
        sty("meta", fontSize=9, textColor=LIGHT, leading=13)))
    s.append(sp(4))
    s.append(hr())

    # ── Authentication ────────────────────────────────────────────────────────
    s.append(Paragraph("Authentication", H2))
    s.append(Paragraph(
        "Every request must include your API key in the <font name='Courier'>X-API-Key</font> header. "
        "Contact Warex Logistics to obtain your key.", BODY))
    s.append(sp(2))
    s.append(code_block(["X-API-Key: your-api-key"]))
    s.append(sp(3))
    s.append(data_table(
        ["Status Code", "Meaning"],
        [["401", "No API key provided — add the X-API-Key header"],
         ["403", "Invalid API key — check your key is correct"]],
        col_widths=[28*mm, 142*mm]
    ))

    # ── Endpoints overview ────────────────────────────────────────────────────
    s.append(Paragraph("Endpoints", H2))
    for m, p, d in [
        ("POST", "/api/v1/orders",                       "Create a new delivery order"),
        ("GET",  "/api/v1/orders/{tracking_number}",     "Retrieve order status and details"),
        ("GET",  "/api/v1/orders/{tracking_number}/track","Get step-by-step tracking timeline"),
    ]:
        s.append(endpoint_pill(m, p, d))
        s.append(sp(2))

    # ── 1. Create Order ───────────────────────────────────────────────────────
    s.append(hr())
    s.append(Paragraph("1. Create Order", H2))
    s.append(Paragraph(
        "Submit a new delivery order. Save the returned <font name='Courier'>tracking_number</font> — "
        "you will need it to check status.", BODY))
    s.append(sp(2))
    s.append(endpoint_pill("POST", "/api/v1/orders", "Create a new delivery order"))
    s.append(Paragraph("Request Headers", H3))
    s.append(data_table(
        ["Header", "Value"],
        [["X-API-Key",    "Your API key"],
         ["Content-Type", "application/json"]],
        col_widths=[45*mm, 125*mm]
    ))
    s.append(Paragraph("Request Body", H3))
    s.append(data_table(
        ["Field", "Type", "Required", "Description"],
        [["customer_name", "string",  "Yes", "Full name of the recipient"],
         ["email",         "string",  "Yes", "Recipient email address"],
         ["phone",         "string",  "Yes", "Recipient phone number"],
         ["address",       "string",  "Yes", "Street address"],
         ["suburb",        "string",  "Yes", "Suburb"],
         ["postcode",      "string",  "Yes", "Postcode"],
         ["state",         "string",  "No",  "State (default: NSW)"],
         ["address2",      "string",  "No",  "Apartment / unit number"],
         ["company",       "string",  "No",  "Recipient company name"],
         ["parcels",       "integer", "No",  "Number of parcels (default: 1)"],
         ["service_level", "string",  "No",  "standard, express, or economy (default: standard)"],
         ["instructions",  "string",  "No",  "Delivery instructions e.g. Leave at front door"],
         ["reference",     "string",  "No",  "Your internal order reference — stored alongside the order"],
         ["weight",        "number",  "No",  "Total parcel weight in kilograms e.g. 2.5"],
         ["zone",          "string",  "No",  "Delivery zone if known"]],
        col_widths=[35*mm, 20*mm, 18*mm, 97*mm]
    ))
    s.append(Paragraph("Example Request", H3))
    s.append(code_block([
        'curl -X POST https://eloquent-cooperation-production-12c5.up.railway.app/api/v1/orders \\',
        '  -H "X-API-Key: your-api-key" \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{',
        '        "customer_name": "Jane Smith",',
        '        "email":         "jane@example.com",',
        '        "phone":         "0412345678",',
        '        "address":       "123 George St",',
        '        "suburb":        "Sydney",',
        '        "state":         "NSW",',
        '        "postcode":      "2000",',
        '        "parcels":       2,',
        '        "service_level": "express",',
        '        "instructions":  "Leave at front door",',
        '        "reference":     "YOUR-ORDER-001"',
        '  }\'',
    ]))
    s.append(sp(3))
    s.append(Paragraph("Success Response — 201 Created", H3))
    s.append(code_block([
        '{',
        '  "success":         true,',
        '  "tracking_number": "WRX-2604-A3F7B1",',
        '  "order_id":        "WRX-2604-A3F7B1",',
        '  "status":          "pending"',
        '}',
    ]))
    s.append(sp(2))
    s.append(Paragraph("Error Response — 400 Bad Request", H3))
    s.append(code_block([
        '{ "success": false, "error": "Missing required fields: email, postcode" }',
    ]))

    # ── 2. Get Order ──────────────────────────────────────────────────────────
    s.append(sp(4))
    s.append(hr())
    s.append(Paragraph("2. Get Order", H2))
    s.append(Paragraph("Retrieve the current status and full details of an order.", BODY))
    s.append(sp(2))
    s.append(endpoint_pill("GET", "/api/v1/orders/{tracking_number}", "Retrieve order status and details"))
    s.append(Paragraph("Example Request", H3))
    s.append(code_block([
        'curl https://eloquent-cooperation-production-12c5.up.railway.app/api/v1/orders/WRX-2604-A3F7B1 \\',
        '  -H "X-API-Key: your-api-key"',
    ]))
    s.append(Paragraph("Success Response — 200 OK", H3))
    s.append(code_block([
        '{',
        '  "success": true,',
        '  "order": {',
        '    "tracking_number": "WRX-2604-A3F7B1",',
        '    "status":          "in_transit",',
        '    "customer":        "Jane Smith",',
        '    "address":         "123 George St",',
        '    "suburb":          "Sydney",',
        '    "state":           "NSW",',
        '    "postcode":        "2000",',
        '    "parcels":         2,',
        '    "service_level":   "express",',
        '    "created_at":      "2026-04-09T10:00:00",',
        '    "driver_id":       "DRV-706"',
        '  }',
        '}',
    ]))
    s.append(Paragraph("Order Statuses", H3))
    s.append(data_table(
        ["Status", "Meaning"],
        [["pending",    "Order received, awaiting driver assignment"],
         ["allocated",  "Driver has been assigned"],
         ["in_transit", "Out for delivery"],
         ["delivered",  "Successfully delivered"],
         ["failed",     "Delivery attempt failed"]],
        col_widths=[30*mm, 140*mm]
    ))

    # ── 3. Track Order ────────────────────────────────────────────────────────
    s.append(sp(4))
    s.append(hr())
    s.append(Paragraph("3. Track Order", H2))
    s.append(Paragraph(
        "Returns a step-by-step tracking timeline. "
        "Useful for displaying progress to your own customers.", BODY))
    s.append(sp(2))
    s.append(endpoint_pill("GET", "/api/v1/orders/{tracking_number}/track", "Get step-by-step tracking timeline"))
    s.append(Paragraph("Example Request", H3))
    s.append(code_block([
        'curl https://eloquent-cooperation-production-12c5.up.railway.app/api/v1/orders/WRX-2604-A3F7B1/track \\',
        '  -H "X-API-Key: your-api-key"',
    ]))
    s.append(Paragraph("Success Response — 200 OK", H3))
    s.append(code_block([
        '{',
        '  "success":         true,',
        '  "tracking_number": "WRX-2604-A3F7B1",',
        '  "current_status":  "in_transit",',
        '  "timeline": [',
        '    { "status": "pending",    "label": "Order Received",   "completed": true  },',
        '    { "status": "allocated",  "label": "Driver Assigned",  "completed": true  },',
        '    { "status": "in_transit", "label": "Out For Delivery", "completed": true  },',
        '    { "status": "delivered",  "label": "Delivered",        "completed": false }',
        '  ]',
        '}',
    ]))

    # ── HTTP Status Codes ─────────────────────────────────────────────────────
    s.append(sp(4))
    s.append(hr())
    s.append(Paragraph("HTTP Status Codes", H2))
    s.append(data_table(
        ["Code", "Meaning"],
        [["200", "Success"],
         ["201", "Order created successfully"],
         ["400", "Bad request — check request body for missing or invalid fields"],
         ["401", "Unauthorised — API key header is missing"],
         ["403", "Forbidden — API key is incorrect"],
         ["404", "Not found — tracking number does not exist"],
         ["500", "Internal server error — contact Warex Logistics support"]],
        col_widths=[20*mm, 150*mm]
    ))

    # ── Code Examples ─────────────────────────────────────────────────────────
    s.append(sp(4))
    s.append(hr())
    s.append(Paragraph("Code Examples", H2))

    s.append(Paragraph("Python", H3))
    s.append(code_block([
        "import requests",
        "",
        "API_KEY  = 'your-api-key'",
        "BASE_URL = 'https://eloquent-cooperation-production-12c5.up.railway.app'",
        "HEADERS  = {'X-API-Key': API_KEY, 'Content-Type': 'application/json'}",
        "",
        "# Create an order",
        "res = requests.post(f'{BASE_URL}/api/v1/orders', headers=HEADERS, json={",
        "    'customer_name': 'Jane Smith',  'email': 'jane@example.com',",
        "    'phone': '0412345678',          'address': '123 George St',",
        "    'suburb': 'Sydney',             'postcode': '2000',",
        "    'reference': 'YOUR-ORDER-001',",
        "})",
        "tracking = res.json()['tracking_number']",
        "print('Created:', tracking)",
        "",
        "# Check status",
        "status = requests.get(f'{BASE_URL}/api/v1/orders/{tracking}', headers=HEADERS)",
        "print(status.json()['order']['status'])",
    ]))
    s.append(sp(3))

    s.append(Paragraph("JavaScript / Node.js", H3))
    s.append(code_block([
        "const BASE_URL = 'https://eloquent-cooperation-production-12c5.up.railway.app';",
        "const HEADERS  = { 'X-API-Key': 'your-api-key', 'Content-Type': 'application/json' };",
        "",
        "// Create an order",
        "const res = await fetch(`${BASE_URL}/api/v1/orders`, {",
        "  method: 'POST', headers: HEADERS,",
        "  body: JSON.stringify({",
        "    customer_name: 'Jane Smith', email: 'jane@example.com',",
        "    phone: '0412345678',         address: '123 George St',",
        "    suburb: 'Sydney',            postcode: '2000',",
        "    reference: 'YOUR-ORDER-001',",
        "  }),",
        "});",
        "const { tracking_number } = await res.json();",
        "",
        "// Check status",
        "const status = await fetch(`${BASE_URL}/api/v1/orders/${tracking_number}`,",
        "  { headers: { 'X-API-Key': 'your-api-key' } });",
        "console.log(await status.json());",
    ]))
    s.append(sp(3))

    s.append(Paragraph("PHP", H3))
    s.append(code_block([
        "$baseUrl = 'https://eloquent-cooperation-production-12c5.up.railway.app';",
        "$apiKey  = 'your-api-key';",
        "",
        "$ch = curl_init(\"$baseUrl/api/v1/orders\");",
        "curl_setopt_array($ch, [",
        "  CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true,",
        "  CURLOPT_HTTPHEADER => [\"X-API-Key: $apiKey\", 'Content-Type: application/json'],",
        "  CURLOPT_POSTFIELDS => json_encode([",
        "    'customer_name' => 'Jane Smith', 'email' => 'jane@example.com',",
        "    'phone' => '0412345678',          'address' => '123 George St',",
        "    'suburb' => 'Sydney',             'postcode' => '2000',",
        "    'reference' => 'YOUR-ORDER-001',",
        "  ]),",
        "]);",
        "$data = json_decode(curl_exec($ch), true);",
        "echo 'Tracking: ' . $data['tracking_number'];",
    ]))

    # ── Footer ────────────────────────────────────────────────────────────────
    s.append(sp(5))
    s.append(hr())
    s.append(sp(2))
    s.append(Paragraph(
        "For API access or integration support contact <font color='#3B82F6'>support@warexlogistics.com.au</font> "
        "or visit <font color='#3B82F6'>warexlogistics.com.au</font>",
        sty("footer", fontSize=9, textColor=LIGHT, leading=13)
    ))

    doc.build(s)
    print(f"✅ PDF saved → {OUTPUT}")


if __name__ == "__main__":
    build()
