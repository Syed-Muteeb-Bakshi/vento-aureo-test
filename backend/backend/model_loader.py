# backend/backend/model_loader.py
import os
import joblib
from pathlib import Path

# model_fetcher has:
#   load_joblib(model_path) -> loads joblib from supabase (cached)
#   load_keras(model_path)  -> loads keras model from supabase (cached)
from model_fetcher import load_joblib as _load_joblib_from_supabase
from model_fetcher import load_keras as _load_keras_from_supabase

# Primary local disk (Render persistent disk recommended)
RENDER_MODEL_ROOT = "/var/models"

# Local repo model root fallback (relative)
LOCAL_MODEL_ROOT = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))

# Supabase availability
SUPABASE_ENABLED = bool(os.environ.get("SUPABASE_PUBLIC_URL"))

def _is_keras_filename(fname: str):
    return any(fname.endswith(ext) for ext in (".keras", ".h5", ".hdf5"))

def _safe_joblib_load(path):
    try:
        return joblib.load(path)
    except Exception as e:
        raise

def _safe_keras_load(path):
    # lazy import here so TF isn't imported at module import time
    from tensorflow import keras
    return keras.models.load_model(path)

def load_model(filename: str, subfolder: str | None = None):
    """
    Universal loader:
      - filename: either a simple filename (e.g. 'rf_tuned.joblib') OR a path-like 'prophet_models/City_prophet.joblib'
      - subfolder: optional folder under model roots (e.g. 'other_models', 'prophet_models', 'hybrid_models/lstm_models')
    Order:
      1) Render persistent disk (/var/models/...)
      2) Local MODEL_DIR (env)
      3) Supabase public bucket via model_fetcher (if enabled)
    Returns:
      - loaded model object (joblib or keras)
    Raises:
      - FileNotFoundError if nothing found
      - Exceptions raised by loader if file invalid
    """
    # Normalize input
    filename = filename.replace("\\", "/")
    if subfolder:
        # if filename already contains a path, do not double join
        if "/" in filename:
            rel_path = filename
        else:
            rel_path = f"{subfolder.rstrip('/')}/{filename}"
    else:
        rel_path = filename

    # 1) Render persistent disk
    render_path = os.path.join(RENDER_MODEL_ROOT, rel_path)
    if os.path.exists(render_path):
        try:
            if _is_keras_filename(render_path):
                return _safe_keras_load(render_path)
            return _safe_joblib_load(render_path)
        except Exception as e:
            # If loading fails on disk, continue to try other sources but log
            print(f"[WARN] Render disk load failed for {render_path}: {e}")

    # 2) Local repo
    local_path = os.path.join(LOCAL_MODEL_ROOT, rel_path)
    if os.path.exists(local_path):
        try:
            if _is_keras_filename(local_path):
                return _safe_keras_load(local_path)
            return _safe_joblib_load(local_path)
        except Exception as e:
            print(f"[WARN] Local model load failed for {local_path}: {e}")

    # 3) Supabase fallback
    if SUPABASE_ENABLED:
        try:
            # For Supabase we pass the bucket-style path "subfolder/filename"
            if _is_keras_filename(rel_path):
                return _load_keras_from_supabase(rel_path)
            return _load_joblib_from_supabase(rel_path)
        except Exception as e:
            print(f"[WARN] Supabase load failed for {rel_path}: {e}")

    # nothing worked
    raise FileNotFoundError(f"Model not found at Render disk, LOCAL_MODEL_ROOT ({LOCAL_MODEL_ROOT}), or Supabase: {rel_path}")
