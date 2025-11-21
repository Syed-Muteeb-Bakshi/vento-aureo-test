#!/usr/bin/env python3
"""
generate_city_coordinates.py

Fetch city coordinates for all Prophet model filenames.

Behavior:
- Prefer listing model filenames from Supabase public storage (SUPABASE_PUBLIC_URL)
- If Supabase listing fails and a local prophet directory exists, fall back to local files
- Writes output to utils/city_coordinates.json by default (same as earlier)
- Set DRY_RUN=1 environment variable to run without writing the JSON file

Notes:
- SUPABASE_PUBLIC_URL should point to:
  https://<project>.supabase.co/storage/v1/object/public/<bucket-name>
  Example:
  https://abcd1234.supabase.co/storage/v1/object/public/vento-aureo-models
"""

import os
import json
import time
import requests
import re
from typing import List, Dict, Optional

# -------------------------
# Configuration / Paths
# -------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# Local prophet dir (fallback only) — kept for convenience if you still have local models
LOCAL_PROPHET_DIR = os.path.join(BASE_DIR, "models", "hybrid_models", "prophet_models")

# Supabase public bucket base URL (set this in environment)
SUPABASE_PUBLIC_URL = os.environ.get(
    "SUPABASE_PUBLIC_URL",
    "https://YOUR-PROJECT.supabase.co/storage/v1/object/public/vento-aureo-models"
)

# Candidate prefixes inside the bucket to search for prophet models
REMOTE_PROPHET_PREFIXES = [
    "hybrid_models/prophet_models",
    "prophet_models"
]

# Output JSON location (kept in the repo)
OUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "city_coordinates.json")
# Local utils output (kept for backwards compatibility)
LEGACY_OUT_FILE = os.path.join(os.path.dirname(__file__), "city_coordinates.json")

# Runtime flags
DRY_RUN = os.environ.get("DRY_RUN", "") not in ("", "0", "false", "False")

# Geocoding delay (seconds) to protect API limits
GEOCODING_DELAY = float(os.environ.get("GEOCODING_DELAY", "0.35"))


# -------------------------
# Helpers
# -------------------------
def _list_remote_prophet_models() -> List[str]:
    """
    List prophet model filenames from Supabase public bucket.
    Uses the Storage list endpoint: <SUPABASE_PUBLIC_URL>?prefix=<prefix>
    Returns list of filename strings (only basename, e.g. 'Delhi_prophet.joblib')
    """
    files = []
    for prefix in REMOTE_PROPHET_PREFIXES:
        url = f"{SUPABASE_PUBLIC_URL}?prefix={prefix}"
        try:
            resp = requests.get(url, timeout=15)
            # Supabase returns JSON list of objects for listing; but be defensive
            if resp.status_code != 200:
                print(f"[WARN] Supabase list for prefix '{prefix}' returned HTTP {resp.status_code}")
                continue
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                print(f"[WARN] Supabase list error for prefix '{prefix}': {data.get('msg', data.get('error'))}")
                continue
            if not isinstance(data, list):
                # Some instances might return an object envelope; attempt to extract
                # Try to find an array under common keys
                if isinstance(data, dict):
                    for k in ("data", "objects", "items"):
                        if k in data and isinstance(data[k], list):
                            data = data[k]
                            break
                if not isinstance(data, list):
                    print(f"[WARN] Unexpected Supabase listing format for prefix '{prefix}'")
                    continue
            for obj in data:
                # objects likely have 'name' field like 'prophet_models/City_prophet.joblib'
                if isinstance(obj, dict) and "name" in obj:
                    name = obj["name"]
                elif isinstance(obj, str):
                    name = obj
                else:
                    continue
                if name.endswith("_prophet.joblib"):
                    base = name.split("/")[-1]
                    files.append(base)
        except Exception as e:
            print(f"[WARN] Could not list Supabase folder '{prefix}': {e}")
            continue
    # unique
    return sorted(list(set(files)))


def _list_local_prophet_models() -> List[str]:
    """Fallback: list local files if present in expected folder"""
    if not os.path.isdir(LOCAL_PROPHET_DIR):
        return []
    files = [f for f in os.listdir(LOCAL_PROPHET_DIR) if f.endswith("_prophet.joblib")]
    return sorted(files)


def extract_city_name(filename: str) -> str:
    """
    Converts filenames like 'A_Coruna_Spain_prophet.joblib' into 'A Coruna Spain'
    """
    name = re.sub(r"_prophet\.joblib$", "", filename, flags=re.IGNORECASE)
    name = name.replace("_", " ")
    return name.strip()


def fetch_coordinates(city: str) -> Optional[Dict]:
    """
    Fetch a single city coordinate using Open-Meteo geocoding.
    Returns dict {city, lat, lon, country} or None on failure.
    """
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(city)}&count=1"
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            print(f"[WARN] Geocoding HTTP {resp.status_code} for {city}")
            return None
        data = resp.json()
        results = data.get("results") or data.get("data") or []
        if not results:
            print(f"[WARN] No coordinates found for '{city}'")
            return None
        first = results[0]
        return {
            "city": city,
            "lat": first.get("latitude") or first.get("lat"),
            "lon": first.get("longitude") or first.get("lon"),
            "country": first.get("country", "")
        }
    except Exception as e:
        print(f"[ERROR] Exception fetching coordinates for {city}: {e}")
        return None


# -------------------------
# Main
# -------------------------
def main():
    print("[INFO] generate_city_coordinates starting...")
    print(f"[INFO] SUPABASE_PUBLIC_URL = {SUPABASE_PUBLIC_URL}")
    print(f"[INFO] DRY_RUN = {DRY_RUN}")

    # 1) Try remote listing first
    files = _list_remote_prophet_models()
    if files:
        print(f"[INFO] Found {len(files)} prophet models from Supabase.")
    else:
        # fallback to local folder
        local_files = _list_local_prophet_models()
        if local_files:
            print(f"[WARN] Supabase listing empty — falling back to local folder: {LOCAL_PROPHET_DIR}")
            files = local_files
        else:
            print("[FATAL] No prophet model filenames found in Supabase or local folder.")
            print("Either upload models to Supabase or restore local prophet_models folder.")
            return

    print("[INFO] Starting coordinate fetch for found cities...")
    output = {}

    for i, fname in enumerate(files):
        city = extract_city_name(fname)
        print(f"[{i+1}/{len(files)}] Fetching → {city}")
        info = fetch_coordinates(city)
        if info:
            output[city] = info
        else:
            # Still add placeholder so downstream UI has knowledge that a city exists
            output[city] = {"city": city, "lat": None, "lon": None, "country": ""}
        time.sleep(GEOCODING_DELAY)

    # Save
    if DRY_RUN:
        print("[DRY_RUN] Completed. Not writing file. Sample output keys:")
        sample_keys = list(output.keys())[:10]
        print(sample_keys)
        return

    # Ensure output directory exists
    out_dir = os.path.dirname(OUT_FILE)
    os.makedirs(out_dir, exist_ok=True)

    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print("\n[SUCCESS] Coordinates saved to:")
    print(OUT_FILE)


if __name__ == "__main__":
    main()
