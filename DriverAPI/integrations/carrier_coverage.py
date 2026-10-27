"""Pinned build artifact loader; no network, GIS dependency or client overrides."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from integrations.draft_rates import LocalityCoveragePolicy

COVERAGE_VERSION = 'nsw-33-councils-locality-candidate-v2-20261027'
COVERAGE_SHA256 = 'f5e34df7186fb8284bef75db2aaa201fdd69c788150b18fee2c292d309b48a2d'
COVERAGE_PATH = Path(__file__).resolve().parents[1] / 'resources' / 'carrier_coverage_v2.json'
FIELDS = {'schema_version','version','boundary','classifications','counts',
          'source_reference','source_review_sha256','licence','attribution',
          'licence_evidence','council_source'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field.')
        result[key] = value
    return result


def validate_document(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError('Unsupported coverage document fields.')
    if (type(data['schema_version']) is not int or data['schema_version'] != 1
            or data['version'] != COVERAGE_VERSION
            or data['boundary'] != 'nsw_sydney_plan_33_councils'):
        raise ValueError('Incompatible coverage document version or boundary.')
    for field in FIELDS - {'schema_version','classifications','counts'}:
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError('Invalid coverage metadata.')
    reference_hash = data['source_review_sha256']
    if len(reference_hash) != 64 or any(c not in '0123456789abcdef' for c in reference_hash):
        raise ValueError('Invalid coverage source hash.')
    if not isinstance(data['classifications'], dict) or not data['classifications']:
        raise ValueError('Missing coverage classifications.')
    if not isinstance(data['counts'], dict) or any(type(n) is not int or n < 0 for n in data['counts'].values()):
        raise ValueError('Invalid coverage counts.')
    if any(not isinstance(status,str) or status not in ('inside','outside','crossing','ambiguous')
           for status in data['classifications'].values()):
        raise ValueError('Invalid coverage status.')
    if dict(Counter(data['classifications'].values())) != data['counts']:
        raise ValueError('Coverage counts mismatch.')
    if any(not isinstance(name,str) or name != ' '.join(name.split()).upper()
           for name in data['classifications']):
        raise ValueError('Coverage names must be canonical.')
    return LocalityCoveragePolicy(data['version'],data['source_reference'],data['classifications'])


def load_coverage(version, path=None):
    """Explicit version selection is required, after commercial policy approval.

    path is for local validation only; service configuration cannot supply paths
    or hashes. The reviewed release pins both artifact version and exact bytes.
    Missing/tampered data raises before route registration, never allows coverage.
    """
    if version != COVERAGE_VERSION:
        raise ValueError('Unsupported configured coverage version.')
    target = COVERAGE_PATH if path is None else Path(path)
    try:
        with target.open('rb') as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
    except OSError:
        raise ValueError('Coverage artifact unavailable.') from None
    if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != COVERAGE_SHA256:
        raise ValueError('Coverage artifact integrity check failed.')
    try:
        data = json.loads(raw, object_pairs_hook=unique_object)
        return validate_document(data)
    except (ValueError, TypeError, UnicodeError):
        raise ValueError('Coverage artifact schema check failed.') from None
