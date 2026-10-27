# Warex Carrier UAT API Reference

API v1 · Contract draft · Test access and final label acceptance pending

This reference describes test rates, test orders and test labels. These endpoints are not yet offered as live services. Test orders cannot be dispatched and do not represent live delivery bookings. Use fictional customer details only.

## Connection and access

Base URL placeholder: `https://YOUR_WAREX_API_BASE_URL`

Warex supplies the integration URL and a dedicated test API key separately. Send it as `X-API-Key: <TEST_API_KEY>` on every request. Operational API keys do not grant test access. Authorised test identity is determined by the service. Request bodies cannot choose a partner identity or switch between live and test access. Unauthorised requests return `403`.

POST requests use `Content-Type: application/json`. Maximum request size is 64 KiB. Monetary values are AUD decimal strings with two decimal places. Weight and declared-value inputs must be decimal strings or integers, not JSON floating-point numbers. Unknown request fields are rejected.

## Rates

`POST /api/v1/uat/rates`

Required body fields: `origin`, `destination`, `parcels`.

Each location requires non-empty string fields `suburb`, `postcode`, `state`, `country`. Postcodes contain four ASCII digits, including leading zeroes. Use `NSW` and ISO country code `AU`. Suburb, state and country are case-insensitive; surrounding and repeated suburb whitespace is normalised. Both pickup and delivery must pass the configured coverage policy. A locality-only policy checks the gazetted locality name, state and country: the supplied postcode is checked for four-digit format only, not validated against the locality. Only localities classified wholly inside coverage are quotable. Outside localities are rejected; ambiguous, boundary-crossing or unknown localities require review. No coverage is inferred from an NSW address alone. No real locality dataset is enabled yet.

`parcels` contains 1–100 parcel objects; 100 is a request batching limit. Each parcel supports:

| Field | Required | Meaning |
| --- | --- | --- |
| `actual_weight_kg` | Yes | Actual parcel weight, greater than zero and no more than 22 kg. Decimal string or integer; at most nine decimal places. |
| `cover_selected` | No | Boolean, default `false`. |
| `declared_value_aud` | When cover selected | Positive parcel value up to AUD 5,000, with at most two decimal places. Above-cap values require separate review and are rejected. Supplying a value alone does not select cover. |

### Pricing

| Actual weight per parcel | Base freight, GST included |
| --- | --- |
| Greater than zero, up to 1 kg | $5.70 |
| Greater than 1 kg, up to 3 kg | $6.70 |
| Greater than 3 kg, up to 5 kg | $7.70 |
| Greater than 5 kg, up to 22 kg | $7.70 + $0.40 × additional kilograms above 5, rounded upward |

Bands are continuous: 1.005 kg costs $6.70 and 3.005 kg costs $7.70. A 5.001 kg parcel costs $8.10; a 6.001 kg parcel costs $8.50. Each parcel is rated separately, and shipment base freight is their sum. The 22 kg limit applies to each parcel, not the combined shipment.

Fuel is excluded from quotes. The 6% fuel levy is invoice-only; this API does not define its invoice calculation basis or apply it to cover.

Cover is optional and excluded unless selected. The charge is 1% of the declared value of each selected parcel, GST included, rounded to the nearest cent using half-up rounding for each parcel, then summed. Do not add GST again. For supported locations, selected cover is included in `total_aud` together with base freight; fuel remains excluded. A parcel value of $5,000 attracts $50.00 cover. Two selected parcels valued at $100.50 each attract $1.01 each, or $2.02 total cover.

Return-to-sender charges are not included in an outbound rate response. This API does not quote or book a return service.

### Example request

The locality and postcode below are fictional test fixtures, not a serviced address. Use Warex-supplied test locations when access is available.

```json
{
  "origin": {"suburb":"Fixture Locality","postcode":"0000","state":"NSW","country":"AU"},
  "destination": {"suburb":"Fixture Locality","postcode":"0000","state":"NSW","country":"AU"},
  "parcels": [
    {"actual_weight_kg":"1","cover_selected":false},
    {"actual_weight_kg":"5.1","cover_selected":false}
  ]
}
```

### Response fields

When both locations are supported and no unresolved charge applies, the response is `200`, with `quote_ready:true`, `test:true` and `total_aud`. For the example above under its fictional test coverage, `base_freight_aud` and `total_aud` are both `"13.80"`.

| Field | Meaning |
| --- | --- |
| `tariff_version`, `coverage_version` | Identifiers of the tariff and coverage list used. Coverage version is null when not configured. |
| `service_code` | `WAREX_STANDARD`; final partner mapping remains subject to agreement. |
| `currency`, `weight_basis`, `pricing_unit` | `AUD`, `actual`, `parcel`. |
| `maximum_parcel_weight_kg` | `"22"`. |
| `boundary_policy` | `0<w<=1; 1<w<=3; 3<w<=5; then ceil(w-5)`. |
| `base_freight_gst_included` | `true`. |
| `base_freight_aud` | Sum of parcel base charges. |
| `parcels` | Ordered breakdown: `parcel_number`, `actual_weight_kg`, `base_freight_aud`, `cover_selected`, `cover_charge_aud`. |
| `cover_charge_aud` | Sum of GST-inclusive cover charges; `"0.00"` when not selected. |
| `cover_gst_included` | `true`; GST is already included in the 1% charge. |
| `fuel_in_quote_aud` | `"0.00"`. |
| `fuel_treatment` | `6_percent_invoice_only_calculation_basis_not_defined_here`. |
| `quote_ready` | Whether a complete rate is available for these inputs. |
| `unresolved_rules` | Empty when ready; otherwise the blocking reasons below. |
| `total_aud` | Present only when `quote_ready:true`. |

`409` reasons: `sydney_boundary_not_configured`, or `locality_coverage_review_required` for ambiguous, crossing or unknown localities. If either end is outside, the response is `422`, including any additional review reason. No final total is supplied while any coverage reason remains.

Additional response fields: `coverage_basis` identifies locality-only or configured-pair matching; `postcode_validation` explicitly identifies format-only or pair validation. Under locality-only coverage, `coverage_classification` contains separate `origin` and `destination` statuses (`inside`, `outside`, `ambiguous`, `crossing`, `unknown`). Review does not automatically create a booking or send a notification.

`422` reason: `origin_or_destination_outside_configured_coverage`. No final total is returned for unsupported locations.

## Create a test order

`POST /api/v1/uat/orders`

Required header: `Idempotency-Key: <UNIQUE_REQUEST_KEY>`

The key must contain 1–128 printable ASCII characters, excluding spaces. Use one key per intended test order. A retry with the same partner, key and normalised body returns the original record. Reusing the key with changed data returns `409` and does not create another record. Different keys can create separate records even when `reference` is identical.

The body includes the same `origin`, `destination`, `parcels` as the rates request, plus:

| Field | Required | Meaning |
| --- | --- | --- |
| `sender` | Yes | Object with `name`, `address`; optional `address2`. |
| `recipient` | Yes | Object with `name`, `address`, `email`, `phone`; optional `address2`. |
| `instructions` | No | String, default empty. |
| `reference` | No | Caller reference, default empty; not an idempotency key. |

Sender/recipient values must be non-empty strings of at most 250 characters. Instructions/reference may be empty and are limited to 250 characters. Text is trimmed. No email, phone or physical-address deliverability validation is performed. Email and phone are stored as test data only; no messages are sent.

Example additional fields to combine with the rates body:

```json
{
  "sender":{"name":"Test Sender","address":"1 Fixture Street"},
  "recipient":{"name":"Test Recipient","address":"2 Fixture Street","email":"test@example.invalid","phone":"000"},
  "instructions":"SYNTHETIC DATA - DO NOT DISPATCH",
  "reference":"TEST-ORDER-001"
}
```

New orders require a complete rate. Otherwise the response is `409` or `422`, with `error:"Shipment is not quotable."`, `test:true` and the rate response under `rate`. No order is created. An existing idempotent replay returns the original stored rate, even if coverage or the tariff later changes.

`201` means a new test record was created; `200` means an idempotent replay. Responses contain:

```json
{
  "success":true,
  "test":true,
  "status":"test_pending",
  "tracking_number":"UAT-<GENERATED_IDENTIFIER>",
  "parcel_ids":["UAT-<GENERATED_IDENTIFIER>-001","UAT-<GENERATED_IDENTIFIER>-002"],
  "created_at":"2026-10-26T10:00:00+00:00",
  "rate":{},
  "replayed":false
}
```

`rate` contains the complete rate snapshot described above; `{}` is abbreviated here. Treat all identifiers as opaque. Test orders have no live dispatch, email, WMS or push-notification effects. They remain `test_pending`; no live delivery milestones are simulated.

## Retrieve a test order or tracking

`GET /api/v1/uat/orders/{tracking_number}` returns the same order envelope, with `replayed:false` and the stored rate snapshot. It does not return the sender/recipient contact fields.

`GET /api/v1/uat/orders/{tracking_number}/track` returns `test:true`, `tracking_number`, `current_status:"test_pending"` and one `events` entry:

```json
{"status":"test_pending","occurred_at":"2026-10-26T10:00:00+00:00","description":"Test order recorded; no live delivery."}
```

Both routes return `404` for an unknown identifier or an order belonging to another test identity.

## Test labels

`GET /api/v1/uat/orders/{tracking_number}/label?format=pdf`

Formats: `pdf` (default) or `html`. The endpoint returns an attachment, not a label URL or base64 JSON response. PDF uses `application/pdf`; HTML uses `text/html`. Each parcel has a distinct identifier and QR code encoding that identifier. No ZPL, linear barcode or printer-language output is provided.

PDF labels contain one 4×6-inch page per parcel, sender and recipient addresses, parcel count, actual weight, instructions and **TEST ONLY - NOT FOR DELIVERY**. HTML provides printable labels with embedded QR images. The final format, barcode and physical printer acceptance must be agreed before operational use.

PDF text is reduced to fit within defined areas; if it still cannot fit at the minimum font size, the endpoint returns `422` rather than silently truncating the address. HTML print pagination may vary by browser. Missing rendering capability returns `503`.

## Errors and client behaviour

| HTTP | Meaning |
| --- | --- |
| `400` | Invalid body, unsupported fields/format, invalid numeric data or missing/invalid idempotency key. |
| `403` | Authorised test access required. |
| `404` | Test order unavailable to this identity. |
| `409` | Quote prerequisites unresolved, or an idempotency key was reused with changed input. |
| `413` | Request exceeds 64 KiB. |
| `422` | Unsupported location or PDF label text cannot fit. |
| `503` | Label renderer unavailable. |

Validation errors use a JSON `error` string. Blocked rate responses instead include `quote_ready:false` and `unresolved_rules`. Unexpected/framework failures may not be JSON: check HTTP status and content type. API responses specify `Cache-Control: no-store`.

Retry an ambiguous creation request with the same idempotency key and identical normalised payload. Do not substitute a new key to retry an unknown outcome. Keep test credentials and customer-like fixture data confidential. Polling limits, retention and deletion procedures will be supplied with test access.
