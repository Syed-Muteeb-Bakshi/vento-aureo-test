import os
import json
import time
import requests
import re

# ============================================================
# FIXED PATH – USE THE REAL PROPHET DIRECTORY
# ============================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PROPHET_DIR = os.path.join(
    BASE_DIR,
    "models",
    "hybrid_models",
    "prophet_models"
)

OUT_FILE = os.path.join(os.path.dirname(__file__), "city_coordinates.json")

# ============================================================
# Helper: Normalize filename → city name
# ============================================================

def extract_city_name(filename):
    """
    Converts filenames like 'A Coruna Spain_prophet.joblib'
    into clean readable names: 'A Coruna Spain'
    """

    name = re.sub(r"_prophet\.joblib$", "", filename)
    name = name.replace("_", " ")
    return name.strip()

# ============================================================
# Fetch coordinates with fail-safes
# ============================================================

def fetch_coordinates(city):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            print(f"[WARN] API failure for {city}: HTTP {r.status_code}")
            return None

        data = r.json()

        if "results" not in data or not data["results"]:
            print(f"[WARN] No coordinates found for {city}")
            return None

        result = data["results"][0]

        return {
            "city": city,
            "lat": result["latitude"],
            "lon": result["longitude"],
            "country": result.get("country", "")
        }

    except Exception as e:
        print(f"[ERROR] Exception fetching coordinates for {city}: {e}")
        return None

# ============================================================
# Main execution
# ============================================================

def main():
    # 1. Validate prophet model directory
    if not os.path.isdir(PROPHET_DIR):
        print(f"[FATAL] Prophet directory not found:\n{PROPHET_DIR}")
        return

    files = [f for f in os.listdir(PROPHET_DIR) if f.endswith("_prophet.joblib")]

    if not files:
        print(f"[FATAL] No Prophet model files found in:\n{PROPHET_DIR}")
        return

    print(f"[INFO] Found {len(files)} Prophet model files.")
    print(f"[INFO] Starting coordinate fetch...\n")

    output = {}

    for i, f in enumerate(files):
        city = extract_city_name(f)
        print(f"[{i+1}/{len(files)}] Fetching → {city}")

        info = fetch_coordinates(city)

        if info:
            output[city] = info

        # Protect API limits: pause briefly
        time.sleep(0.35)

    # Save
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print("\n[SUCCESS] Coordinates saved to:")
    print(OUT_FILE)


if __name__ == "__main__":
    main()
