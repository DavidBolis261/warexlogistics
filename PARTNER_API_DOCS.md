# Warex Logistics — Partner API Documentation

**Base URL:** `https://eloquent-cooperation-production-12c5.up.railway.app`  
**Version:** v1  
**Format:** JSON  

---

## Authentication

Every request must include your API key in the `X-API-Key` header.

```
X-API-Key: your-api-key
```

If your key is missing or incorrect you will receive:

| Status | Meaning |
|--------|---------|
| `401`  | No API key provided |
| `403`  | Invalid API key |

Contact Warex Logistics to receive your API key.

---

## Endpoints

### 1. Create Order

Submit a new delivery order to the Warex Logistics platform.

```
POST /api/v1/orders
```

**Headers**

| Header | Value |
|--------|-------|
| `X-API-Key` | Your API key |
| `Content-Type` | `application/json` |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_name` | string | ✅ | Full name of the recipient |
| `email` | string | ✅ | Recipient email address |
| `phone` | string | ✅ | Recipient phone number |
| `address` | string | ✅ | Street address |
| `suburb` | string | ✅ | Suburb |
| `postcode` | string | ✅ | Postcode |
| `state` | string | | State (default: `NSW`) |
| `address2` | string | | Apartment / unit number |
| `company` | string | | Recipient company name |
| `parcels` | integer | | Number of parcels (default: `1`) |
| `service_level` | string | | `standard`, `express`, or `economy` (default: `standard`) |
| `instructions` | string | | Delivery instructions |
| `reference` | string | | Your internal order reference — stored alongside the order |
| `weight` | number | | Total parcel weight in kilograms e.g. `2.5` |
| `zone` | string | | Delivery zone if known |

**Example Request**

```bash
curl -X POST https://eloquent-cooperation-production-12c5.up.railway.app/api/v1/orders \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Jane Smith",
    "email": "jane@example.com",
    "phone": "0412345678",
    "address": "123 George St",
    "suburb": "Sydney",
    "state": "NSW",
    "postcode": "2000",
    "parcels": 2,
    "service_level": "express",
    "instructions": "Leave at front door",
    "reference": "YOUR-ORDER-001"
  }'
```

**Success Response — 201 Created**

```json
{
  "success": true,
  "tracking_number": "WRX-2604-A3F7B1",
  "order_id": "WRX-2604-A3F7B1",
  "status": "pending"
}
```

Save the `tracking_number` — you will need it to check status or tracking.

**Error Response — 400 Bad Request**

```json
{
  "success": false,
  "error": "Missing required fields: email, postcode"
}
```

---

### 2. Get Order

Retrieve the current status and details of an order.

```
GET /api/v1/orders/{tracking_number}
```

**Headers**

| Header | Value |
|--------|-------|
| `X-API-Key` | Your API key |

**Example Request**

```bash
curl https://eloquent-cooperation-production-12c5.up.railway.app/api/v1/orders/WRX-2604-A3F7B1 \
  -H "X-API-Key: your-api-key"
```

**Success Response — 200 OK**

```json
{
  "success": true,
  "order": {
    "tracking_number": "WRX-2604-A3F7B1",
    "status": "in_transit",
    "customer": "Jane Smith",
    "address": "123 George St",
    "suburb": "Sydney",
    "state": "NSW",
    "postcode": "2000",
    "parcels": 2,
    "service_level": "express",
    "created_at": "2026-04-09T10:00:00",
    "driver_id": "DRV-706"
  }
}
```

**Order Statuses**

| Status | Meaning |
|--------|---------|
| `pending` | Order received, awaiting driver assignment |
| `allocated` | Driver has been assigned |
| `in_transit` | Out for delivery |
| `delivered` | Successfully delivered |
| `failed` | Delivery attempt failed |

**Error Response — 404 Not Found**

```json
{
  "success": false,
  "error": "Order not found"
}
```

---

### 3. Track Order

Returns a step-by-step tracking timeline for an order — useful for displaying progress to your customers.

```
GET /api/v1/orders/{tracking_number}/track
```

**Headers**

| Header | Value |
|--------|-------|
| `X-API-Key` | Your API key |

**Example Request**

```bash
curl https://eloquent-cooperation-production-12c5.up.railway.app/api/v1/orders/WRX-2604-A3F7B1/track \
  -H "X-API-Key: your-api-key"
```

**Success Response — 200 OK**

```json
{
  "success": true,
  "tracking_number": "WRX-2604-A3F7B1",
  "current_status": "in_transit",
  "timeline": [
    { "status": "pending",    "label": "Order Received",   "completed": true  },
    { "status": "allocated",  "label": "Driver Assigned",  "completed": true  },
    { "status": "in_transit", "label": "Out For Delivery", "completed": true  },
    { "status": "delivered",  "label": "Delivered",        "completed": false }
  ]
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Order created successfully |
| `400` | Bad request — check your request body for missing or invalid fields |
| `401` | Unauthorised — API key missing |
| `403` | Forbidden — API key invalid |
| `404` | Not found — tracking number does not exist |
| `500` | Internal server error — contact Warex Logistics support |

---

## Code Examples

### Python

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "https://eloquent-cooperation-production-12c5.up.railway.app"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Create an order
response = requests.post(f"{BASE_URL}/api/v1/orders", headers=HEADERS, json={
    "customer_name": "Jane Smith",
    "email": "jane@example.com",
    "phone": "0412345678",
    "address": "123 George St",
    "suburb": "Sydney",
    "postcode": "2000",
    "parcels": 1,
    "service_level": "standard",
    "reference": "YOUR-ORDER-001"
})
data = response.json()
tracking_number = data["tracking_number"]
print(f"Order created: {tracking_number}")

# Check status
status = requests.get(f"{BASE_URL}/api/v1/orders/{tracking_number}", headers=HEADERS)
print(status.json())
```

### JavaScript / Node.js

```javascript
const API_KEY = 'your-api-key';
const BASE_URL = 'https://eloquent-cooperation-production-12c5.up.railway.app';

// Create an order
const response = await fetch(`${BASE_URL}/api/v1/orders`, {
  method: 'POST',
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    customer_name: 'Jane Smith',
    email: 'jane@example.com',
    phone: '0412345678',
    address: '123 George St',
    suburb: 'Sydney',
    postcode: '2000',
    parcels: 1,
    service_level: 'standard',
    reference: 'YOUR-ORDER-001',
  }),
});

const data = await response.json();
console.log('Tracking number:', data.tracking_number);

// Check status
const statusRes = await fetch(`${BASE_URL}/api/v1/orders/${data.tracking_number}`, {
  headers: { 'X-API-Key': API_KEY },
});
console.log(await statusRes.json());
```

### PHP

```php
<?php
$apiKey  = 'your-api-key';
$baseUrl = 'https://eloquent-cooperation-production-12c5.up.railway.app';

// Create an order
$ch = curl_init("$baseUrl/api/v1/orders");
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => true,
    CURLOPT_HTTPHEADER     => ["X-API-Key: $apiKey", "Content-Type: application/json"],
    CURLOPT_POSTFIELDS     => json_encode([
        'customer_name' => 'Jane Smith',
        'email'         => 'jane@example.com',
        'phone'         => '0412345678',
        'address'       => '123 George St',
        'suburb'        => 'Sydney',
        'postcode'      => '2000',
        'parcels'       => 1,
        'service_level' => 'standard',
        'reference'     => 'YOUR-ORDER-001',
    ]),
]);
$data = json_decode(curl_exec($ch), true);
echo "Tracking number: " . $data['tracking_number'];
?>
```

---

## Support

For API access, integration support, or to report issues please contact:

**Warex Logistics**  
Email: support@warexlogistics.com.au  
Website: warexlogistics.com.au
