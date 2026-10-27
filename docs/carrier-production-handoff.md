# Production handoff — approved scope, execution deferred

User approved deployment to the existing service, interim manual coverage review, dedicated Starshipit UAT key, additive test-only table and enabling restricted UAT access. Sending the key to Ron remains unapproved. OpenSSL restoration completed separately. This document supersedes prior pending-approval wording for those approved actions. No key generated, migration run, commit/push or deployment performed in this handoff.

## Exact checkout and commit route

Repository /Users/davidbolis/Documents/ChatGPT/warexlogistics. Branch codex/restore-railway. HEAD 8d8905c925712e1e294c74e283ef081e4cff8169. Origin https://github.com/DavidBolis261/warexlogistics.git. Upstream origin/codex/restore-railway; local cached ref is equal (0 ahead / 0 behind), not a fresh remote verification.

Nine runtime paths and matching SHA-256 hashes are in carrier-uat-release-manifest.json. Only tracked changes are four server wiring lines and the ReportLab pin. New modules/resource/tests/docs are untracked. No changes were staged. Preserve unrelated files under docs/tools; do not use git add . or stage whole directories.

After parent verifies live source configuration and directs commit/push:

```sh
git fetch origin codex/restore-railway
git rev-list --left-right --count HEAD...origin/codex/restore-railway
git diff --check
git add --pathspec-from-file=docs/carrier-release-paths.txt
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
git commit -m "Add isolated carrier UAT rates orders and labels"
git rev-parse HEAD
git push origin HEAD:codex/restore-railway
```

Stop if fresh remote history diverges, unexpected staged files appear, or any pinned runtime hash changes. Do not reset, clean, force-push or overwrite user edits. The allowlist includes 37 explicit paths (runtime, tests, source attribution, validation tools and handoff/path-list documents) as listed in the file; use the file as the exact authority rather than directory globs. Record resulting commit SHA; none exists yet. Confirm Railway watches this exact branch, service root DriverAPI and unchanged Procfile before pushing, because an automatic deployment may begin immediately.

## Service configuration (exact nonsecret values)

First deploy with CARRIER_UAT_ENABLED=false; do not change existing DATABASE_URL, PORT, EXTERNAL_API_KEY, driver settings or Starshipit import-worker settings.

For the final enabled rollout:

- CARRIER_UAT_ENABLED=true
- CARRIER_UAT_COVERAGE_VERSION=nsw-33-councils-locality-candidate-v2-20261027
- CARRIER_UAT_CREDENTIALS_JSON=[{"partner_id":"starshipit-uat","token_sha256":"<SHA256_OF_NEW_DEDICATED_TEST_SECRET>"}]

The digest placeholder is not a deployable value. Generate a fresh high-entropy secret only in the approved secure execution flow; store the plaintext in an approved secret store and configure only its lowercase SHA-256 digest. Do not print/store plaintext in chat, source, build logs or shell arguments. Do not send it to Ron. Header X-API-Key supplies the dedicated token over HTTPS. Never reuse the operational EXTERNAL_API_KEY. Token scope is only this partner's UAT rates/orders/labels/tracking; no live dispatch or messages. Restart applies changes and revocation.

Artifact: DriverAPI/resources/carrier_coverage_v2.json, 130011 bytes, SHA-256 f5e34df7186fb8284bef75db2aaa201fdd69c788150b18fee2c292d309b48a2d. Loader pins both version/hash and validates schema. Interim behavior: 755 names inside; 3697 outside; 46 crossing and 18 ambiguous require review. Unknown names also require review. Postcodes are format-checked only. No expansion or numerical tolerance.

## Backup and migration sequence

1. Parent verifies exact production DB identity and prior successful deployment/revision via its working connection. Record rollback deployment ID and current nonsecret feature settings.
2. Verify an existing fresh provider backup or create the approved backup if no new cost is involved. Record successful completion, timestamp, restore point and restoration procedure. Stop if backup verification or restore capability is unavailable. A pg_restore --list alone verifies archive readability, not successful restore. Do not dump production data into this repository or overwrite production to test recovery.
3. Deploy the committed code with UAT disabled. Confirm terminal deployment success, /health=200 and UAT routes=404. Existing docs endpoint is a known pre-existing 500 and is not a readiness probe.
4. Execute the additive migration through the already-authorized service execution context, using its existing DATABASE_URL. This is easiest because the service has the driver and private DB route; it avoids copying credentials or opening public DB access. Do not open a new Railway login/reconnect flow in this child. If the parent's connector cannot execute a command, use its existing authenticated database SQL console for the equivalent SQL below; stop/report if neither execution surface exists.

In DriverAPI working directory (use an inline Python command/file via the execution tool, never interpolate the URL into shell arguments):

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from integrations.carrier_persistence import migrate_carrier_uat, SQLAlchemyUATStore
engine = create_engine(make_url(os.environ['DATABASE_URL']).set(drivername='postgresql+psycopg2'),
    hide_parameters=True, connect_args={'connect_timeout':10,
    'options':'-c lock_timeout=5000 -c statement_timeout=30000'})
try:
    migrate_carrier_uat(engine)
    SQLAlchemyUATStore(engine).check_schema()
finally:
    engine.dispose()
```

Equivalent additive SQL on the same schema/search_path used by the app:

```sql
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS carrier_uat_orders (
    partner TEXT NOT NULL,
    request_key TEXT NOT NULL,
    digest TEXT NOT NULL,
    tracking TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (partner, request_key),
    UNIQUE (tracking)
);
COMMIT;
```

Inspect columns/nullability and constraints if the table already exists; IF NOT EXISTS does not repair an incompatible table. Verify app role SELECT/INSERT access using existing grants; do not silently broaden roles/permissions. No operational table migration/backfill. Do not use DataManager initialization as the migration entrypoint.

5. Configure the approved test identity/digest and dataset version, then set CARRIER_UAT_ENABLED=true and restart/redeploy. Confirm terminal success before reporting availability.
6. Run only fictional-data UAT smoke checks: no key→403; covered rate→200; Sydney/The Rocks/unknown→409 and Gosford→422 with no total; create→201, identical retry→200 same UAT ID, changed body/same key→409; PDF attachment→200 and test watermark; tracking→test_pending. Verify no operational rows/queues/messages changed. No test emails, WMS calls, dispatch or paid carrier activity. Keep the test key out of logs/output.

## Contract for Ron

POST /api/v1/uat/rates; POST /api/v1/uat/orders (Idempotency-Key required); GET /api/v1/uat/orders/{tracking}; GET .../track; GET .../label?format=pdf|html. Dedicated X-API-Key required throughout. Rates use actual weight per parcel, 22kg cap, AUD/GST-inclusive base and optional 1% cover; fuel excluded. One 4x6-inch PDF per parcel, QR identifier, TEST ONLY watermark. No live delivery statuses. This supplies test rates/orders/labels, but Ron must accept the paths, body/response schema and PDF/QR format; it is not proof of partner acceptance. Existing /api/v1/orders and driver endpoints remain unchanged by UAT wiring.

## Rollback

Set CARRIER_UAT_ENABLED=false and restart, verify /health and UAT=404. Revoke digest if access needs withdrawal. Redeploy recorded previous artifact if a code/dependency regression persists. Keep the additive UAT table and records; do not drop it or restore the entire database as ordinary rollback. Never retry uncertain creation with a new idempotency key. If migration fails before commit, rollback that transaction and leave feature disabled.

## Evidence and limits

63 aggregate repository tests pass (network blocked, synthetic fixtures); six geometry tests and PostgreSQL 18.6 actual transaction/restart/PDF tests pass. Post-restoration PostgreSQL rerun also passes. Runtime resource hash matches checkout. Existing API disabled-mode regression includes real server registration with mocked DB/worker and unchanged auth behavior. Whole Railway runtime/image/SSL and provider backup verification still need the parent-side steps above; no production action happened here. Existing /api/driver/docs500 is confirmed baseline source, not test-fixture error.

## Parent-verified live configuration (10:49 UTC)

Source DavidBolis261/warexlogistics, branch codex/restore-railway, rootDirectory /DriverAPI. RAILPACK build environment V3. Start command gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 driver_api_server:app; healthcheck /health. Domain driverapi-production-b594.up.railway.app, target port 5000, region europe-west4-drams3a. No staged configuration. Existing variable names only: DATABASE_URL, EMAIL_FROM_ADDRESS, ENABLE_DRIVER_LOGIN, PORT, RESEND_API_KEY, SITE_DOMAIN, TZ. No CARRIER_UAT flags exist, so the initial code deployment stays disabled without a preliminary variable change. No values were retrieved by this child.

All nine runtime release files, including resources/carrier_coverage_v2.json, are inside DriverAPI. The loader uses a path relative to its module and does not read root docs/tests/tools. Root docs/tests are evidence and development tooling, not runtime dependencies. Production migration should use the inline invocation above within the deployed DriverAPI root; the root-level validation script is not required in the image.
