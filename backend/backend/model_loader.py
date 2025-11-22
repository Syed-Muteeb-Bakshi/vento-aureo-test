import os
import joblib
import requests
from tensorflow import keras

# -------------------------------------------
# DIRECTORIES
# -------------------------------------------

# Where uploaded RF/LSTM models are stored on Render free-tier
LOCAL_MODEL_DIR = "/tmp/local_models"
os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)

# Where joblib/keras files are cached after remote download
MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/tmp/model_cache")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

# Supabase public bucket base URL
SUPABASE_PUBLIC_URL = os.environ.get("SUPABASE_PUBLIC_URL")
if SUPABASE_PUBLIC_URL and SUPABASE_PUBLIC_URL.endswith("/"):
    SUPABASE_PUBLIC_URL = SUPABASE_PUBLIC_URL[:-1]


# -------------------------------------------
# HELPERS
# -------------------------------------------

def _local_path_for(filename):
    return os.path.join(LOCAL_MODEL_DIR, filename)


def _cache_path_for(filename):
    safe = filename.replace("/", "_")
    return os.path.join(MODEL_CACHE_DIR, safe)


def _download_from_supabase(remote_path, cache_path):
    """
    Downloads a model file from Supabase:
    remote_path example: "prophet_models/Delhi_prophet.joblib"
    """

    if not SUPABASE_PUBLIC_URL:
        raise FileNotFoundError("SUPABASE_PUBLIC_URL not set")

    url = f"{SUPABASE_PUBLIC_URL}/{remote_path}"
    print(f"[REMOTE] downloading → {url}")

    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        raise FileNotFoundError(f"Supabase file not found: {url}")

    with open(cache_path, "wb") as f:
        f.write(r.content)

    return cache_path


# -------------------------------------------
# MASTER LOAD FUNCTION
# -------------------------------------------

def load_model(filename, folder):
    """
    Load a model file with priority:
    1. Local uploaded model  (/tmp/local_models)
    2. Cached remote file    (/tmp/model_cache)
    3. Download from Supabase bucket
    """

    # -------------------------------
    # 1. LOCAL UPLOADED MODEL
    # -------------------------------
    local_path = _local_path_for(filename)
    if os.path.exists(local_path):
        print(f"[LOCAL] Using uploaded model → {local_path}")
        if filename.endswith(".joblib"):
            return joblib.load(local_path)
        else:
            return keras.models.load_model(local_path)

    # -------------------------------
    # 2. CACHED REMOTE FILE
    # -------------------------------
    cache_path = _cache_path_for(filename)
    if os.path.exists(cache_path):
        print(f"[CACHE] Loading cached model → {cache_path}")
        if filename.endswith(".joblib"):
            return joblib.load(cache_path)
        else:
            return keras.models.load_model(cache_path)

    # -------------------------------
    # 3. SUPABASE: DOWNLOAD
    # -------------------------------
    remote_path = f"{folder}/{filename}"
    downloaded = _download_from_supabase(remote_path, cache_path)

    print(f"[REMOTE] Model downloaded & cached → {downloaded}")

    if filename.endswith(".joblib"):
        return joblib.load(downloaded)
    else:
        return keras.models.load_model(downloaded)
