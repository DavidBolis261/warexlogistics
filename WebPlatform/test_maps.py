"""
Quick test script for Google Maps geocoding
"""
import os
from dotenv import load_dotenv
from utils.google_maps import geocode_address, get_route_polyline, decode_polyline

# Load environment
load_dotenv()

print("Testing Google Maps Integration")
print("=" * 50)

# Test geocoding
test_address = "123 George Street"
test_suburb = "Sydney"
test_state = "NSW"
test_postcode = "2000"

print(f"\nGeocoding: {test_address}, {test_suburb} {test_state} {test_postcode}")
coords = geocode_address(test_address, test_suburb, test_state, test_postcode)

if coords:
    print(f"✅ Success! Coordinates: {coords}")
    lat, lng = coords
    print(f"   Latitude: {lat}")
    print(f"   Longitude: {lng}")
else:
    print("❌ Geocoding failed")
    print("Check your GOOGLE_PLACES_API_KEY in .env file")

# Test another address
test_address2 = "1 William Street"
test_suburb2 = "Darlinghurst"
print(f"\nGeocoding: {test_address2}, {test_suburb2} {test_state} {test_postcode}")
coords2 = geocode_address(test_address2, test_suburb2, test_state, test_postcode)

if coords2:
    print(f"✅ Success! Coordinates: {coords2}")
else:
    print("❌ Geocoding failed")

# Test routing if both addresses succeeded
if coords and coords2:
    print(f"\nTesting route between both addresses...")
    waypoints = [
        {'lat': coords[0], 'lng': coords[1]},
        {'lat': coords2[0], 'lng': coords2[1]}
    ]

    polyline = get_route_polyline(waypoints)

    if polyline:
        print(f"✅ Route polyline received (length: {len(polyline)} chars)")
        decoded = decode_polyline(polyline)
        print(f"   Decoded to {len(decoded)} coordinate points")
    else:
        print("❌ Routing failed")

print("\n" + "=" * 50)
print("Test complete!")
