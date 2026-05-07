import requests

FUEL_API_URL = "https://api.data.gov.my/data-catalogue?id=fuelprice&limit=1&sort=-date"

def get_latest_fuel_prices():
    try:
        response = requests.get(FUEL_API_URL, timeout=10)
        response.raise_for_status()

        json_data = response.json()

        # data.gov.my returns a list directly, not wrapped in a "data" key
        if isinstance(json_data, list) and len(json_data) > 0:
            latest = json_data[0]
        elif isinstance(json_data, dict) and "data" in json_data:
            latest = json_data["data"][0]
        else:
            raise ValueError("Unexpected API response format")

        return {
            "date": latest.get("date"),
            "ron95": latest.get("ron95"),
            "ron97": latest.get("ron97"),
            "diesel": latest.get("diesel")
        }

    except Exception as e:
        print("Fuel price API error:", e)

        # fallback values so your app does not crash
        return {
            "date": None,
            "ron95": 2.05,
            "ron97": 3.47,
            "diesel": 2.15
        }