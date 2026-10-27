# Carrier UAT enablement checkpoint

Local implementation only. No configuration, migration or deployment has been executed.

The existing Flask service calls configure_carrier_uat after registering existing APIs. CARRIER_UAT_ENABLED defaults off: no new routes, database access or migration. When explicitly true it requires the existing PostgreSQL SQLAlchemy engine, a pre-migrated carrier_uat_orders table and valid trusted access records. Invalid enabled configuration fails startup rather than falling back to shared operational access.

CARRIER_UAT_CREDENTIALS_JSON is a list of objects with partner_id and token_sha256. Only SHA-256 digests of separately issued high-entropy random test tokens belong here. X-API-Key is checked against those digests using constant-time comparison. No credentials have been issued. Records bind access exclusively to UAT routes and one partner. Restart applies rotation/revocation. Never reuse EXTERNAL_API_KEY or a password. Credential provisioning, secure delivery and enabling configuration require separate approval.

The additive migration function integrations.carrier_persistence.migrate_carrier_uat(engine) creates only the dedicated carrier_uat_orders table and unique constraints. It is never called at startup. Review database backup and privileges before approved execution. Disabling the flag removes routes on restart and preserves test records; rollback does not drop data. Retention/deletion policy remains to be established before test access.

Persistence uses transactions and unique (partner, request_key) conflicts, never overwrites prior payloads, and scopes reads by partner. No operational orders, dispatch, WMS or email interfaces are imported by the UAT modules. Existing service workers remain unchanged; UAT records are not placed in their queues.

Geography defaults to None. A strict packaged loader now supports explicit CARRIER_UAT_COVERAGE_VERSION=nsw-33-councils-locality-candidate-v2-20261027 after policy approval; no setting was activated. Rates/orders fail closed if no policy is selected. A selected missing/corrupt/incompatible artifact fails startup before routes register. No environment-provided or client-provided postcode list is accepted. Official licensed source and boundary classifications are recorded in docs/coverage-review. Acceptance of interim manual review remains unresolved.

Runtime manifest adds reportlab>=4.0,<5. No installation performed. PostgreSQL SQL is compilation-checked; local transactional tests use temporary SQLite via the same SQLAlchemy adapter. Actual PostgreSQL 18.6 concurrency, migration and restart validation now passes; see docs/coverage-review/postgres18-validation.json. Railway-specific SSL/networking and production migration execution remain untested. No production database was accessed.

Contract: POST /api/v1/uat/rates; POST /api/v1/uat/orders with Idempotency-Key; GET /api/v1/uat/orders/{tracking}; GET .../track; GET .../label?format=pdf|html. All require X-API-Key. Partner reference is docs/partner-api/Warex_Carrier_UAT_API_Reference.md. Ron must still accept the contract and PDF/QR format.
