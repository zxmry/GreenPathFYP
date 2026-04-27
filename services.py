# services.py
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import ssl
import urllib.request

# --- Part 1: Geocoding (Address -> Coordinates) ---
def get_coordinates(address):
    """Converts an address string to (latitude, longitude)."""
    # Create an unverified SSL context to fix certificate issues
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Create a custom opener with the SSL context
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
    urllib.request.install_opener(opener)
    
    geolocator = Nominatim(
        user_agent="greenpath_fyp_student_project",
        timeout=10
    )
    
    try:
        location = geolocator.geocode(address)
        if location:
            print(f"✓ Geocoding successful: {address} -> ({location.latitude}, {location.longitude})")
            return (location.latitude, location.longitude)
        else:
            print(f"✗ Geocoding failed: {address} (No results)")
            return None
    except Exception as e:
        print(f"✗ Geocoding error for {address}: {e}")
        return None

# --- Part 2: OSRM (Coordinates -> Distance Matrix) ---
def get_distance_matrix(coordinates):
    """Fetches the distance matrix from OSRM."""
    if not coordinates or len(coordinates) < 2:
        print("✗ Distance matrix: Need at least 2 coordinates")
        return None

    # Format: "lon1,lat1;lon2,lat2" (OSRM requires Longitude first)
    coords_string = ";".join([f"{lon},{lat}" for lat, lon in coordinates])
    
    base_url = "http://router.project-osrm.org/table/v1/driving/"
    url = f"{base_url}{coords_string}?annotations=distance"
    
    print(f"📡 Fetching distance matrix for {len(coordinates)} locations...")

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✓ Distance matrix received successfully")
            return data.get('distances') # Returns the 2D matrix
        else:
            print(f"✗ OSRM error: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ OSRM Error: {e}")
        return None

def get_route_shape(coordinates):
    """
    Gets the detailed road geometry for an ordered list of coordinates.
    """
    if not coordinates or len(coordinates) < 2:
        print("✗ Route shape: Need at least 2 coordinates")
        return None

    # Format: "lon1,lat1;lon2,lat2"
    coords_string = ";".join([f"{lon},{lat}" for lat, lon in coordinates])
    
    # We use the 'route' service (not 'table') and ask for 'overview=full' (detailed shape)
    # 'geometries=geojson' gives us an easy list of points
    base_url = "http://router.project-osrm.org/route/v1/driving/"
    url = f"{base_url}{coords_string}?overview=full&geometries=geojson"
    
    print(f"📡 Fetching route shape for {len(coordinates)} points...")

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # OSRM returns [lon, lat], but Leaflet needs [lat, lon]. We must swap them.
            if 'routes' in data and len(data['routes']) > 0:
                geometry = data['routes'][0]['geometry']['coordinates']
                # Swap [lon, lat] -> [lat, lon]
                swapped_geometry = [[lat, lon] for lon, lat in geometry]
                print("✓ Route shape received successfully")
                return swapped_geometry
        else:
            print(f"✗ OSRM route error: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ OSRM Route Error: {e}")
        return None