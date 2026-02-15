"""
Google Maps utilities for geocoding, routing, and distance calculations.
"""
import os
import requests
from typing import List, Dict, Tuple, Optional
from functools import lru_cache


def get_api_key() -> str:
    """Get Google Places API key from environment or Streamlit secrets."""
    try:
        import streamlit as st
        api_key = st.secrets.get('google_places_api_key', '')
        if api_key:
            return api_key
    except:
        pass

    return os.getenv('GOOGLE_PLACES_API_KEY', '')


@lru_cache(maxsize=500)
def geocode_address(address: str, suburb: str = '', state: str = 'NSW', postcode: str = '', country: str = 'Australia') -> Optional[Tuple[float, float]]:
    """
    Geocode an address to get latitude and longitude.

    Args:
        address: Street address
        suburb: Suburb name
        state: State code (default: NSW)
        postcode: Postal code
        country: Country (default: Australia)

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    api_key = get_api_key()
    if not api_key:
        return None

    # Build full address string
    full_address_parts = [address]
    if suburb:
        full_address_parts.append(suburb)
    if state:
        full_address_parts.append(state)
    if postcode:
        full_address_parts.append(postcode)
    if country:
        full_address_parts.append(country)

    full_address = ', '.join(filter(None, full_address_parts))

    try:
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'address': full_address,
            'key': api_key
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        if data.get('status') == 'OK' and data.get('results'):
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])

    except Exception as e:
        print(f"Geocoding error for {full_address}: {e}")

    return None


def get_route_polyline(waypoints: List[Dict[str, float]]) -> Optional[str]:
    """
    Get a route polyline from Google Directions API for multiple waypoints.

    Args:
        waypoints: List of dicts with 'lat' and 'lng' keys

    Returns:
        Encoded polyline string or None if routing fails
    """
    api_key = get_api_key()
    if not api_key or len(waypoints) < 2:
        return None

    try:
        origin = f"{waypoints[0]['lat']},{waypoints[0]['lng']}"
        destination = f"{waypoints[-1]['lat']},{waypoints[-1]['lng']}"

        # Build waypoints string for intermediate stops
        waypoint_str = ''
        if len(waypoints) > 2:
            intermediate = waypoints[1:-1]
            waypoint_str = '|'.join([f"{wp['lat']},{wp['lng']}" for wp in intermediate])

        url = 'https://maps.googleapis.com/maps/api/directions/json'
        params = {
            'origin': origin,
            'destination': destination,
            'key': api_key,
            'mode': 'driving'
        }

        if waypoint_str:
            params['waypoints'] = f"optimize:true|{waypoint_str}"

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('status') == 'OK' and data.get('routes'):
            # Return the encoded polyline
            return data['routes'][0]['overview_polyline']['points']

    except Exception as e:
        print(f"Routing error: {e}")

    return None


def calculate_distance_matrix(origins: List[Dict[str, float]], destinations: List[Dict[str, float]]) -> Optional[Dict]:
    """
    Calculate distance and duration between multiple origins and destinations.

    Args:
        origins: List of origin points with 'lat' and 'lng'
        destinations: List of destination points with 'lat' and 'lng'

    Returns:
        Distance matrix data or None if request fails
    """
    api_key = get_api_key()
    if not api_key or not origins or not destinations:
        return None

    try:
        origins_str = '|'.join([f"{o['lat']},{o['lng']}" for o in origins])
        destinations_str = '|'.join([f"{d['lat']},{d['lng']}" for d in destinations])

        url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {
            'origins': origins_str,
            'destinations': destinations_str,
            'key': api_key,
            'mode': 'driving'
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(f"Distance matrix error: {e}")

    return None


def decode_polyline(polyline_str: str) -> List[Tuple[float, float]]:
    """
    Decode a Google Maps encoded polyline string into lat/lng coordinates.

    Args:
        polyline_str: Encoded polyline string

    Returns:
        List of (latitude, longitude) tuples
    """
    coordinates = []
    index = 0
    lat = 0
    lng = 0

    while index < len(polyline_str):
        # Decode latitude
        result = 0
        shift = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        # Decode longitude
        result = 0
        shift = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng

        coordinates.append((lat / 1e5, lng / 1e5))

    return coordinates
