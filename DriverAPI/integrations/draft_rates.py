"""Pure per-parcel tariff and explicit coverage policy. No live wiring or I/O."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
from typing import FrozenSet, Tuple, Mapping
from types import MappingProxyType

TARIFF_VERSION = 'sydney-actual-per-parcel-2026-10-26-local'
CENT = Decimal('0.01')


def decimal_value(value, name):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(name + ' must be a decimal string or integer, not a float.')
    if isinstance(value, str) and len(value) > 40:
        raise ValueError(name + ' is too long.')
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(name + ' must be finite numeric data.') from None
    if not number.is_finite():
        raise ValueError(name + ' must be finite numeric data.')
    # Bound precision/exponents for deterministic money operations and resource use.
    if len(number.as_tuple().digits) > 18 or number.as_tuple().exponent < -9 or number.as_tuple().exponent > 9:
        raise ValueError(name + ' has unsupported precision; use at most 9 decimal places.')
    return number


def money(value):
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), '.2f')


@dataclass(frozen=True)
class DraftFreight:
    actual_weight_kg: Decimal
    base_freight_aud: Decimal
    weight_basis: str = 'actual'
    boundary_policy: str = 'continuous_up_to_1_then_3_then_5'
    currency: str = 'AUD'
    gst_included: bool = True
    fuel_treatment: str = 'invoice_only_excluded_from_quote'
    invoice_fuel_rate: Decimal = Decimal('0.06')


def calculate_draft_base_freight(actual_weight_kg):
    """Confirmed tariff: continuous bands, then ceil(excess kg), max 22kg/parcel."""
    weight = decimal_value(actual_weight_kg, 'actual_weight_kg')
    if weight <= 0 or weight > 22:
        raise ValueError('Each parcel must weigh more than zero and at most 22kg.')
    if weight <= 1:
        amount = Decimal('5.70')
    elif weight <= 3:
        amount = Decimal('6.70')
    elif weight <= 5:
        amount = Decimal('7.70')
    else:
        amount = Decimal('7.70') + Decimal('0.40') * (weight - 5).to_integral_value(rounding=ROUND_CEILING)
    return DraftFreight(weight, amount)


def normalise_location(location):
    if not isinstance(location, dict) or set(location) != {'suburb', 'postcode', 'state', 'country'}:
        raise ValueError('Locations require exactly suburb, postcode, state and country.')
    if any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in location.values()):
        raise ValueError('Location fields must be non-empty strings of at most 100 characters.')
    postcode = location['postcode'].strip()
    if len(postcode) != 4 or not postcode.isascii() or not postcode.isdigit():
        raise ValueError('postcode must contain four ASCII digits.')
    return {'suburb':' '.join(location['suburb'].split()).upper(), 'postcode':postcode,
            'state':location['state'].strip().upper(), 'country':location['country'].strip().upper()}


@dataclass(frozen=True)
class CoveragePolicy:
    """Exact locality/postcode pairs from an approved boundary, supplied by server.

    No shipped defaults: existing dispatch zones are partial and not authoritative.
    Test policies are fixtures only and must never be promoted as Sydney coverage.
    """
    version: str
    locality_postcodes: FrozenSet[Tuple[str, str]]

    def __post_init__(self):
        if not self.version or not self.locality_postcodes:
            raise ValueError('Coverage requires a version and explicit locality/postcode pairs.')
        pairs = frozenset((normalise_location({'suburb':s, 'postcode':p, 'state':'NSW', 'country':'AU'})['suburb'], p.strip())
                          for s, p in self.locality_postcodes)
        object.__setattr__(self, 'locality_postcodes', pairs)

    def contains(self, location):
        return location['state'] == 'NSW' and location['country'] == 'AU' and (
            location['suburb'], location['postcode']) in self.locality_postcodes



@dataclass(frozen=True)
class LocalityCoveragePolicy:
    """Versioned NSW locality classification; never validates postcode membership.

    Trusted build-time data only. Crossing/ambiguous/unknown localities require
    review; only wholly inside localities can be offered a quote. No real dataset
    is bundled. Source reference must identify the reviewed dataset snapshot.
    """
    version: str
    source_reference: str
    classifications: Mapping[str, str]

    def __post_init__(self):
        if (not isinstance(self.version, str) or not self.version.strip()
                or not isinstance(self.source_reference, str) or not self.source_reference.strip()
                or not isinstance(self.classifications, Mapping) or not self.classifications):
            raise ValueError('Coverage requires version, source and explicit classifications.')
        checked = {}
        for name, status in self.classifications.items():
            if not isinstance(name, str) or not name.strip() or len(name) > 100:
                raise ValueError('Invalid locality name.')
            normal = ' '.join(name.split()).upper()
            if status not in ('inside', 'outside', 'ambiguous', 'crossing') or normal in checked:
                raise ValueError('Invalid or duplicate locality classification.')
            checked[normal] = status
        object.__setattr__(self, 'classifications', MappingProxyType(checked))

    def classify(self, location):
        if location['state'] != 'NSW' or location['country'] != 'AU':
            return 'outside'
        return self.classifications.get(location['suburb'], 'unknown')

    def contains(self, location):
        return self.classify(location) == 'inside'


def normalise_rate_request(body):
    if not isinstance(body, dict) or set(body) != {'origin', 'destination', 'parcels'}:
        raise ValueError('Supply exactly origin, destination and parcels.')
    if not isinstance(body['parcels'], list) or not 1 <= len(body['parcels']) <= 100:
        raise ValueError('Supply 1-100 parcels per request (API batch limit).')
    parcels=[]
    for parcel in body['parcels']:
        if not isinstance(parcel, dict) or set(parcel) - {'actual_weight_kg','cover_selected','declared_value_aud'}:
            raise ValueError('Unsupported parcel fields.')
        freight=calculate_draft_base_freight(parcel.get('actual_weight_kg'))
        selected=parcel.get('cover_selected',False)
        if type(selected) is not bool:
            raise ValueError('cover_selected must be a boolean.')
        normal={'actual_weight_kg':format(freight.actual_weight_kg.normalize(),'f'), 'cover_selected':selected}
        if 'declared_value_aud' in parcel:
            value=decimal_value(parcel['declared_value_aud'],'declared_value_aud')
            if value <= 0 or value > 5000:
                raise ValueError('Declared parcel values must be greater than zero and at most AUD 5000; above-cap terms require review.')
            if value != value.quantize(CENT):
                raise ValueError('declared_value_aud must have at most two decimal places.')
            normal['declared_value_aud']=money(value)
        if selected and 'declared_value_aud' not in normal:
            raise ValueError('Selected cover requires declared_value_aud.')
        parcels.append(normal)
    return {'origin':normalise_location(body['origin']), 'destination':normalise_location(body['destination']), 'parcels':parcels}


def calculate_rate(body, coverage=None):
    request=normalise_rate_request(body)
    blockers=[]
    if coverage is None:
        blockers.append('sydney_boundary_not_configured')
    elif isinstance(coverage, LocalityCoveragePolicy):
        statuses = {side:coverage.classify(request[side]) for side in ('origin', 'destination')}
        if 'outside' in statuses.values():
            blockers.append('origin_or_destination_outside_configured_coverage')
        if any(status in ('ambiguous', 'crossing', 'unknown') for status in statuses.values()):
            blockers.append('locality_coverage_review_required')
    elif not coverage.contains(request['origin']) or not coverage.contains(request['destination']):
        blockers.append('origin_or_destination_outside_configured_coverage')
    lines=[]; base=Decimal('0'); cover=Decimal('0')
    for index, parcel in enumerate(request['parcels'],1):
        charge=calculate_draft_base_freight(parcel['actual_weight_kg']).base_freight_aud
        premium=Decimal('0')
        if parcel['cover_selected']:
            premium=(Decimal(parcel['declared_value_aud'])*Decimal('0.01')).quantize(CENT,rounding=ROUND_HALF_UP)
        base+=charge;cover+=premium
        lines.append(dict(parcel_number=index, actual_weight_kg=parcel['actual_weight_kg'],
                          base_freight_aud=money(charge), cover_selected=parcel['cover_selected'],
                          cover_charge_aud=money(premium)))
    result={'tariff_version':TARIFF_VERSION, 'coverage_version':coverage.version if coverage else None,
            'service_code':'WAREX_STANDARD', 'currency':'AUD', 'weight_basis':'actual',
            'pricing_unit':'parcel', 'maximum_parcel_weight_kg':'22',
            'boundary_policy':'0<w<=1; 1<w<=3; 3<w<=5; then ceil(w-5)',
            'base_freight_gst_included':True, 'base_freight_aud':money(base), 'parcels':lines,
            'cover_charge_aud':money(cover),
            'cover_gst_included':True,
            'fuel_in_quote_aud':'0.00', 'fuel_treatment':'6_percent_invoice_only_calculation_basis_not_defined_here',
            'quote_ready':not blockers, 'unresolved_rules':blockers}
    if isinstance(coverage, LocalityCoveragePolicy):
        result['coverage_basis'] = 'gazetted_locality_name_state_country'
        result['postcode_validation'] = 'format_only_not_matched_to_locality'
        result['coverage_classification'] = statuses
    else:
        result['coverage_basis'] = 'locality_postcode_pairs' if coverage else 'not_configured'
        result['postcode_validation'] = 'configured_pair_match' if coverage else 'format_only_not_matched_to_locality'
    # Never present an unsupported shipment as a payable total.
    if not blockers:
        result['total_aud']=money(base+cover)
    return result
