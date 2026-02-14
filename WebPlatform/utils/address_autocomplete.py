"""
Address autocomplete using Google Places API
"""

import os
import requests


def search_addresses(search_term):
    """
    Search for addresses using Google Places API Autocomplete.
    Returns a list of tuples: (description, place_id) for fetching full details.
    """
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY', '')

    if not api_key or not search_term:
        return []

    # Focus on Australian addresses
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        'input': search_term,
        'key': api_key,
        'components': 'country:au',  # Restrict to Australia
        'types': 'address',  # Only street addresses
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                # Store predictions globally so we can fetch place_id later
                predictions = data.get('predictions', [])
                # Return just descriptions for display
                return [pred['description'] for pred in predictions]
    except Exception as e:
        print(f"Address autocomplete error: {e}")

    return []


def get_place_id_from_description(description):
    """
    Get place_id from a description by doing another autocomplete search.
    This is a workaround since streamlit-searchbox only returns the string value.
    """
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY', '')

    if not api_key or not description:
        return None

    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        'input': description,
        'key': api_key,
        'components': 'country:au',
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                predictions = data.get('predictions', [])
                # Find exact match
                for pred in predictions:
                    if pred['description'] == description:
                        return pred['place_id']
                # Return first result if no exact match
                if predictions:
                    return predictions[0]['place_id']
    except Exception as e:
        print(f"Place ID lookup error: {e}")

    return None


def get_address_details(place_id):
    """
    Get detailed address components from a place_id.
    Returns a dict with street, suburb, state, postcode, etc.
    """
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY', '')

    if not api_key or not place_id:
        return None

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'key': api_key,
        'fields': 'address_components',
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                components = data.get('result', {}).get('address_components', [])
                return parse_address_components(components)
    except Exception as e:
        print(f"Address details error: {e}")

    return None


def parse_address_components(components):
    """
    Parse Google Places address components into our format.
    """
    result = {
        'street_number': '',
        'route': '',
        'suburb': '',
        'state': '',
        'postcode': '',
        'country': 'Australia',
    }

    for comp in components:
        types = comp.get('types', [])

        if 'street_number' in types:
            result['street_number'] = comp.get('long_name', '')
        elif 'route' in types:
            result['route'] = comp.get('long_name', '')
        elif 'locality' in types:
            result['suburb'] = comp.get('long_name', '')
        elif 'administrative_area_level_1' in types:
            result['state'] = comp.get('short_name', '')
        elif 'postal_code' in types:
            result['postcode'] = comp.get('long_name', '')
        elif 'country' in types:
            result['country'] = comp.get('long_name', '')

    # Combine street number and route
    address = f"{result['street_number']} {result['route']}".strip()
    result['address'] = address

    return result


def parse_simple_address(address_string):
    """
    Parse a simple address string from Google Places autocomplete.

    Examples:
    - "123 George Street, Sydney NSW 2000, Australia"
    - "45 Pitt Street, Sydney NSW, Australia"
    - "10 Main Road, Suburb Name NSW 2000, Australia"
    """
    if not address_string:
        return None

    # Split by comma
    parts = [p.strip() for p in address_string.split(',')]

    if len(parts) < 2:
        return {'address': address_string, 'suburb': '', 'state': 'NSW', 'postcode': ''}

    # First part is street address
    address = parts[0]

    # Initialize defaults
    suburb = ''
    state = 'NSW'
    postcode = ''

    # Process all parts to find state and postcode
    import re

    for part in parts:
        # Look for state code (NSW, VIC, etc.)
        state_match = re.search(r'\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b', part, re.IGNORECASE)
        if state_match:
            state = state_match.group(1).upper()

        # Look for 4-digit postcode
        postcode_match = re.search(r'\b(\d{4})\b', part)
        if postcode_match:
            postcode = postcode_match.group(1)

        # Extract suburb (usually second part, before state/postcode)
        if part != parts[0] and part.lower() != 'australia':
            # Remove state and postcode from this part to get suburb
            cleaned = re.sub(r'\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b', '', part, flags=re.IGNORECASE)
            cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
            cleaned = cleaned.strip()
            if cleaned and not suburb:
                suburb = cleaned

    return {
        'address': address,
        'suburb': suburb,
        'state': state,
        'postcode': postcode,
        'country': 'Australia',
    }
