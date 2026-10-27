# Carrier UAT release preflight — prepared, not executed

## Local checks

From repository root, with the already available test environments:

```sh
/tmp/warex-pg-test-venv/bin/python -B tools/carrier_validation/run_regression.py
/tmp/warex-boundary-build-venv/bin/python tools/carrier_validation/test_geometry.py -v
/tmp/warex-pg-test-venv/bin/python -B tools/carrier_validation/validate_postgres.py --pg-bin /opt/homebrew/Cellar/postgresql@18/18.6_1/bin
/tmp/warex-pg-test-venv/bin/python -m pip check
git diff --check
```

Aggregate tests clear inherited configuration and block outbound sockets. The actual Flask startup module is exercised with a fake manager and mocked worker/email modules. Disabled UAT preserves existing routes, health response, external-key auth failure/validation status codes and mocked worker registration; it creates no UAT routes or records. Existing driver/access and outbound Starshipit tests also run against temporary data/mocks. This is not a production startup test.

Known baseline defect: GET /api/driver/docs has non-JSON sets/Ellipsis in its examples and returns 500. Its function AST matches HEAD exactly; the regression checks that it is unchanged and confirms serialization failure. Not fixed in this preflight. Do not use that endpoint as a successful readiness probe.

Dependency check reports no broken installed requirements. This checks installed distributions, not whether every declared app requirement is installed. The local environment lacks cryptography, declared by the app; whole production-environment validation remains pending. Runtime ReportLab is pinned at tested 4.4.10; existing requirement ranges are unchanged. Geometry dependencies stay build-only. Exact test top-level pins do not constitute a full transitive/hash lock.

## Approval and code gates before live rollout

1. Agree whether manual coverage review for 46 crossing and 18 ambiguous names is acceptable for interim UAT. No unsupported name is silently included. The review candidate currently admits 755 names.
2. The trusted, version/hash/schema-checked loader is implemented. After policy approval, explicitly select CARRIER_UAT_COVERAGE_VERSION=nsw-33-councils-locality-candidate-v2-20261027. Without that setting, coverage remains None and no new quotable orders can be created. Missing/corrupt/incompatible selected data fails startup before routes register. Review endpoint responses and fixture addresses with Ron. Do not use documentation as executable configuration.
3. Approve production additive migration, credential provisioning, secure delivery destination, test retention and enabling access. Deployment was previously authorized; these access/database decisions remain distinct. No credential values belong in source, docs, chat or logs.
4. Identify the exact existing Railway service/environment/database and current deployed revision through the parent's working connection; verify approved code diff, dependency build and rollback artifact. No new hosted service is required. Keep unrelated edits out of the release artifact.

## Configuration and scope

- CARRIER_UAT_ENABLED: absent/false keeps all UAT routes absent. Only case-insensitive true enables setup. Enabled invalid config or missing table fails startup.
- CARRIER_UAT_CREDENTIALS_JSON: server-side list of objects with partner_id and token_sha256. Partner IDs match [A-Za-z0-9_-]{1,64}; digests are distinct lowercase SHA-256 hex strings. No raw token in this setting. No wildcard/live access. Multiple digests may map to the same partner for rotation.
- X-API-Key: dedicated randomly generated high-entropy test bearer secret, sent over HTTPS. Provisioning would use at least 32 random bytes; runtime accepts 32–256 printable ASCII characters. Issuance has NOT occurred.
- DATABASE_URL: existing app database URL; do not create/change it. UAT reuses data_manager.store.engine with postgresql+psycopg2. No separate UAT database environment variable.
- EXTERNAL_API_KEY and STARSHIPIT_API_KEY / STARSHIPIT_SUBSCRIPTION_KEY remain unchanged and do not grant UAT access. Native test carrier direction is Starshipit → Warex.
- CARRIER_UAT_COVERAGE_VERSION: absent means no coverage; the only accepted value in this release is nsw-33-councils-locality-candidate-v2-20261027. It selects the packaged hash-pinned artifact. No client/environment path, hash override or locality list is accepted. Selecting this setting requires policy approval; its presence in documentation is not approval.

Scope: dedicated token permits rates, creation and reads/labels/tracking for that partner's test records only. No operational booking, dispatch, WMS or customer-message capability. Revocation/rotation takes effect after config update and restart. No expiry/rate-limit mechanism is implemented here; agree operational policy before opening access.

## Backup and additive migration procedure — future approved execution only

Use the existing provider backup/snapshot workflow where available; record completion, timestamp, database identity, encryption/access and restore procedure before migration. If using a CLI dump, use an approved secure execution context with existing libpq PG* connection variables (never place a URL/password on a command line):

```sh
pg_dump --format=custom --no-owner --file="$BACKUP_FILE"
pg_restore --list "$BACKUP_FILE"
```

BACKUP_FILE must be an approved private encrypted location outside a public repo; protect any production data and do not print it. Listing the dump proves readability, not successful restoration: verify a restore in an approved isolated destination, or document provider restore verification. Do not overwrite production to test restore. Stop if backup verification is unavailable.

Keep CARRIER_UAT_ENABLED absent/false. Run the following only in the approved existing service context with current DATABASE_URL already provided; it imports no DataManager, workers or operational initialization:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from integrations.carrier_persistence import migrate_carrier_uat, SQLAlchemyUATStore
url = make_url(os.environ['DATABASE_URL']).set(drivername='postgresql+psycopg2')
engine = create_engine(url, hide_parameters=True,
    connect_args={'connect_timeout': 10,
                  'options': '-c lock_timeout=5000 -c statement_timeout=30000'})
try:
    migrate_carrier_uat(engine)
    SQLAlchemyUATStore(engine).check_schema()
finally:
    engine.dispose()
```

Run with DriverAPI as the working/import directory. Migration creates only carrier_uat_orders with text columns partner/request_key/digest/tracking/payload; primary key(partner,request_key), unique(tracking), non-null fields. It performs no destructive changes or data backfill and does not modify operational tables. If table exists, separately verify columns, nullability and unique constraints before enabling: create_all is not a schema upgrader. Runtime role needs SELECT/INSERT on this table; do not expand grants without approval. Migration identity needs CREATE only for approved execution. Do not issue privileges automatically.

## Release, safe smoke test and rollback

Deploy reviewed artifact with UAT disabled first. Verify terminal deployment status, /health=200, existing API authentication behavior and /api/v1/uat/rates=404. Do not call operational order creation. After approved migration, loader and credentials are ready, enable and restart the same service. Check unauthorized UAT request=403, covered synthetic rate=200, unsupported/review-required location=422/409 with no total, and synthetic test create=201 then identical replay=200 with same ID; changed replay=409. Fetch PDF/track with correct identity and confirm cross-partner reads=404. Check no operational records/queues/messages were created using approved read-only evidence. Use only fictional address/contact data and real approved covered locality identifiers. Partner acceptance of PDF/QR format remains separate from deployment health.

Rollback: set CARRIER_UAT_ENABLED=false (or remove it) and restart; verify UAT=404 and health/legacy routes. If code/dependency regression remains, redeploy recorded prior artifact/revision. Retain the additive UAT table and test records; do not drop tables or restore the whole DB as a routine rollback. Revoke dedicated access by removing its digest and restarting if required. Stop and investigate unexpected operational effects. Never retry an uncertain create with a new idempotency key.

## Minimal OpenSSL restoration option — NOT executed

Read-only otool evidence shows both installed PostgreSQL postgres and libpq link to /opt/homebrew/opt/openssl@4/lib/libssl.4.dylib and libcrypto.4.dylib. They do not rely on generic libssl.dylib. OpenSSL 3.6.4 remains installed at its versioned paths.

After explicit link-change approval, the smallest Homebrew-managed candidate is:

```sh
HOMEBREW_NO_AUTO_UPDATE=1 brew unlink openssl@4
HOMEBREW_NO_AUTO_UPDATE=1 brew link --force openssl@3
```

This unlinks generic symlinks and links the retained OpenSSL 3 keg; it does not uninstall either version or delete installed library files. Do not use --overwrite. First record current relevant symlink targets and check for collisions; stop if any non-symlink file or unexpected target would be affected. Preserve /opt/homebrew/opt/openssl@4 and verify PostgreSQL's explicit dependencies resolve after relinking. Verify generic openssl/header/libssl/libcrypto/.pc targets point to 3, then rerun temporary PG validation. If relinking 3 fails, relink 4 to restore the recorded current state rather than overwrite conflicts.

The /opt/homebrew/opt/openssl alias presently points to 4; its pre-install target was not captured. Do not change that alias by assumption. This proposal restores known generic OpenSSL 3 paths, not a proven byte-for-byte historical symlink inventory.

A read-only Homebrew dry-run was attempted and hit a sandbox symlink-operation denial while traversing include/openssl. It was not retried with write privileges. Key targets (generic executable/header and both versioned opt paths) were rechecked and unchanged. Link modification needs its own approved execution; no claim that the entire proposed command sequence was successfully simulated.

Risk versus evidence: generic consumers may change ABI or lose .3 paths; no unrelated application failure has been observed or tested. PostgreSQL's versioned linkage supports keeping it installed. Railway uses its own environment and was not changed by this local Homebrew installation.
