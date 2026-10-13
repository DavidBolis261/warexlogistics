# Starshipit integration

Built against the [official API reference](https://api-docs.starshipit.com/) on 13 October 2026. Open **Starshipit** in the Warex administrator sidebar. Public partner and driver accounts cannot access these controls.

## Supported workflow

1. Choose a carrier name/code and order groups, then receive matching orders. The carrier match is exact and case-insensitive. Importing every carrier requires an explicit selection.
2. Warex imports recipient/contact details, pickup details, delivery instructions and parcel count. The complete source order (including products, weights, packages and original tracking numbers) is retained in the private integration snapshot.
3. Each source account/order ID maps to a stable Warex order and tracking number. Repeated imports do not create another order. Pending, unassigned orders can receive address changes. Dispatch assignments, delivery outcomes and evidence are preserved once work has started.
4. Dispatch normally through Orders, Drivers and Route Planning. Delivered outcomes are reconciled into a persistent outbound queue. The worker also catches bulk completion paths. Network failures and rate limits keep updates pending; account/validation errors require review and retry.
5. Review and queue address edits separately. The sender checks the current remote state before sending an address update.

Imports deliberately bypass customer emails and WMS writes. They skip archived orders and non-outgoing shipments. They do not purchase labels, manifest shipments, change carrier tracking numbers, or create new orders in Starshipit.

## Configuration, when ready

Set on **both Dashboard and DriverAPI**:

| Variable | Purpose |
| --- | --- |
| `STARSHIPIT_API_KEY` | Starshipit API key |
| `STARSHIPIT_SUBSCRIPTION_KEY` | Starshipit subscription key |
| `STARSHIPIT_ACCOUNT` | Stable account label; default `primary`. Change the label when switching to a different account, not when rotating keys for the same account. |

For background syncing, also set on **DriverAPI**:

| Variable | Purpose |
| --- | --- |
| `STARSHIPIT_SYNC_ENABLED=true` | Start the background worker |
| `STARSHIPIT_SYNC_INTERVAL_SECONDS=300` | Optional polling interval; minimum 60 seconds |

The worker only starts when enabled and both credentials are present. It flushes outbound updates each cycle; incoming polling additionally requires **Automatically receive matching orders** in the Starshipit page. Manual receive/send controls work without the background worker once credentials are present. There are no dummy credentials, automatic activations, or new paid Railway services.

## API contract and limitations

- Both documented authentication headers are sent only to the fixed HTTPS Starshipit API host. Redirects are refused.
- Incoming: paginated unshipped/shipped lists and recently-printed shipments. Summary records are hydrated by numeric ID. The completed poll saves an overlapping cursor; failures retain the previous cursor for retry.
- Outgoing: `PUT /api/orders` with the linked numeric `order_id`. Delivered uses the documented `Delivered` order status. Address updates are restricted to unshipped/saved orders.
- Starshipit restricts edits after labels are printed. Warex does **not** guess equivalents for allocated, in-transit or failed courier tracking events. Those remain local. The public API referenced here does not establish a way to upload Warex photos/signatures or arbitrary carrier tracking events. A carrier-specific agreement/API would need separate verification for that scope.
- The documented Starshipit webhook is for courier tracking notifications; it is not a new-order feed. This integration receives new orders by polling instead of claiming a new-order webhook exists.
- Outbound success means Starshipit accepted the request. Marketplace writeback and branded notifications are controlled by Starshipit and are not guaranteed by this integration.

## Reliability and verification

Private tables `starshipit_orders`, `starshipit_jobs` and `starshipit_locks` are created automatically in the shared database. Jobs survive restarts; account-scoped leases prevent simultaneous polling/sending by Dashboard and DriverAPI. Supported PUTs are repeatable if a response is lost. Provider response bodies and authentication headers are never persisted in error messages. Snapshots contain customer order data and follow the same database access/backup controls as Warex orders.

Tests use isolated SQLite databases and mocked Starshipit responses. They cover authentication headers, missing credentials, rate limits, pagination, account isolation, duplicate imports, dispatch/evidence preservation, queue persistence, retries, stale delivery protection and post-print edit restrictions. Run `python -m unittest discover -s tests -v`.

Before operational use with credentials: test account access, import a controlled order with the correct carrier filter, verify its mapping in both products, send an address update before printing, and confirm a controlled Delivered writeback. This live provider validation remains outstanding until credentials are supplied.
