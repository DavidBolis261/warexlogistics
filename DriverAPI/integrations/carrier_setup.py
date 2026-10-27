"""Disabled-by-default same-service UAT wiring; no credential issuance or DDL."""
import hashlib
import hmac
import json
import re
from api.carrier_preview import TestIdentity, create_carrier_preview_blueprint
from integrations.carrier_persistence import SQLAlchemyUATStore


def identity_resolver(records):
    """Trusted server configuration contains only SHA-256 token digests.

    Tokens must be separately issued high-entropy random secrets, not passwords.
    No shared operational API key is accepted. Rotation/revocation takes effect
    on service restart; retain multiple records for a partner during rotation.
    """
    if not isinstance(records, list) or not records:
        raise ValueError('UAT access records are required.')
    checked = []
    seen = set()
    for record in records:
        if (not isinstance(record, dict) or set(record) != {'partner_id', 'token_sha256'}
                or not isinstance(record['partner_id'], str)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', record['partner_id'])
                or not isinstance(record['token_sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', record['token_sha256'])
                or record['token_sha256'] in seen):
            raise ValueError('Invalid or duplicate UAT access record.')
        seen.add(record['token_sha256'])
        checked.append((record['token_sha256'], record['partner_id']))

    def resolve(request):
        token = request.headers.get('X-API-Key', '')
        if not 32 <= len(token) <= 256 or not token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in token):
            return None
        digest = hashlib.sha256(token.encode('ascii')).hexdigest()
        identity = None
        for expected, partner in checked:
            if hmac.compare_digest(expected, digest):
                identity = TestIdentity(partner, True)
        return identity
    return resolve


def configure_carrier_uat(app, operational_store, environ, coverage=None):
    """No DB access or route registration unless explicitly enabled.

    Coverage is injected by trusted server code; absent coverage fails closed.
    A pre-existing migrated table is required. Enabling never creates it.
    """
    if environ.get('CARRIER_UAT_ENABLED', '').lower() != 'true':
        return False
    try:
        records = json.loads(environ.get('CARRIER_UAT_CREDENTIALS_JSON', ''))
    except (TypeError, ValueError):
        raise ValueError('Valid UAT credential configuration is required.') from None
    resolver = identity_resolver(records)
    configured_version = environ.get('CARRIER_UAT_COVERAGE_VERSION', '')
    if configured_version:
        if coverage is not None:
            raise ValueError('Use one trusted coverage source only.')
        from integrations.carrier_coverage import load_coverage
        coverage = load_coverage(configured_version)
    engine = getattr(operational_store, 'engine', None)
    if engine is None or engine.dialect.name != 'postgresql':
        raise ValueError('Carrier UAT requires the existing PostgreSQL engine.')
    store = SQLAlchemyUATStore(engine)
    store.check_schema()
    app.register_blueprint(create_carrier_preview_blueprint(resolver, store, coverage))
    return True
