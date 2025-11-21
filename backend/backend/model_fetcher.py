# backend/backend/model_fetcher.py
import os
import joblib
import requests
import errno
from pathlib import Path

# optional lazy tensorflow import only when needed
def _lazy_keras():
    from tensorflow import keras
    return keras

# PUBLIC URL for Supabase storage (example: https://<project>.supabase.co/storage/v1/object/public/models)
SUPABASE_PUBLIC_URL = os.environ.get("SUPABASE_PUBLIC_URL")  # set this in Render env
MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))

# cache location on the server (ephemeral)
CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/tmp/model_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cached_path(model_path: str) -> str:
    """Return a local cached filename for a model_path (safe path)."""
    safe = model_path.replace("/", "__")
    return os.path.join(CACHE_DIR, safe)


def _local_candidate(model_path: str) -> str:
    """Return local filesystem candidate full path for a model_path (MODEL_DIR/<model_path>)."""
    return os.path.join(MODEL_DIR, model_path)


def _download(url: str, dest: str, timeout: int = 60):
    """Download file from url to dest (simple)."""
    r = requests.get(url, timeout=timeout, stream=True)
    if r.status_code != 200:
        raise FileNotFoundError(f"Failed to download model from {url} (status {r.status_code})")
    # write in streaming mode
    tmp = dest + ".part"
    with open(tmp, "wb") as fh:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                fh.write(chunk)
    os.replace(tmp, dest)


def load_joblib(model_path: str):
    """
    Load a joblib serialized file.
    model_path is a relative path inside the model root, e.g. "prophet_models/city_prophet.joblib".
    Local fallback: MODEL_DIR/model_path
    Remote fallback: SUPABASE_PUBLIC_URL + "/" + model_path
    Cached to /tmp/model_cache.
    """
    # 1) If local exists, load directly (fast)
    local_candidate = _local_candidate(model_path)
    if os.path.exists(local_candidate):
        return joblib.load(local_candidate)

    # 2) try cached file
    cache_file = _cached_path(model_path)
    if os.path.exists(cache_file):
        return joblib.load(cache_file)

    # 3) remote download using SUPABASE_PUBLIC_URL
    if SUPABASE_PUBLIC_URL:
        url = f"{SUPABASE_PUBLIC_URL.rstrip('/')}/{model_path.lstrip('/')}"
        try:
            _download(url, cache_file)
            return joblib.load(cache_file)
        except Exception as e:
            # pass up a readable error
            raise FileNotFoundError(f"Could not download model from {url}: {e}")

    raise FileNotFoundError(f"Model not found locally ({local_candidate}) and SUPABASE_PUBLIC_URL not set.")


def load_keras(model_path: str):
    """
    Load a keras model. model_path can be e.g. "hybrid_models/lstm_models/London.keras"
    Follows same local -> cache -> remote order.
    """
    local_candidate = _local_candidate(model_path)
    if os.path.exists(local_candidate):
        keras = _lazy_keras()
        return keras.models.load_model(local_candidate)

    cache_file = _cached_path(model_path)
    if os.path.exists(cache_file):
        keras = _lazy_keras()
        return keras.models.load_model(cache_file)

    if SUPABASE_PUBLIC_URL:
        url = f"{SUPABASE_PUBLIC_URL.rstrip('/')}/{model_path.lstrip('/')}"
        try:
            _download(url, cache_file)
            keras = _lazy_keras()
            return keras.models.load_model(cache_file)
        except Exception as e:
            raise FileNotFoundError(f"Could not download keras model from {url}: {e}")

    raise FileNotFoundError(f"Keras model not found locally ({local_candidate}) and SUPABASE_PUBLIC_URL not set.")
