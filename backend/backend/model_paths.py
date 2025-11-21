# backend/backend/model_paths.py
import os

# Directory where app.py lives (backend/backend)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Local model root (inside repo) — used for local dev
LOCAL_MODEL_ROOT = os.path.join(APP_ROOT, "models")

# Subfolders (local)
PATH_OTHER_MODELS = os.path.join(LOCAL_MODEL_ROOT, "other_models")
PATH_PROPHET_MODELS = os.path.join(LOCAL_MODEL_ROOT, "prophet_models")
PATH_HYBRID_MODELS = os.path.join(LOCAL_MODEL_ROOT, "hybrid_models")
PATH_IOT_MODEL = os.path.join(LOCAL_MODEL_ROOT, "iot_model")

# Ensure MODEL_DIR env var points to LOCAL_MODEL_ROOT if not set
os.environ.setdefault("MODEL_DIR", LOCAL_MODEL_ROOT)

# Helper to resolve a path inside the model root (for debugging)
def resolve_local(path_fragment: str):
    return os.path.join(LOCAL_MODEL_ROOT, path_fragment)
# backend/backend/model_paths.py
import os

# Directory where this file lives (backend/backend)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Default MODEL_DIR environment variable (points to backend/backend/models)
DEFAULT_MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(APP_ROOT, "models"))

# Individual model directories (local)
PATH_OTHER_MODELS = os.path.join(DEFAULT_MODEL_DIR, "other_models")
PATH_PROPHET_MODELS = os.path.join(DEFAULT_MODEL_DIR, "prophet_models")
PATH_HYBRID_MODELS = os.path.join(DEFAULT_MODEL_DIR, "hybrid_models")
PATH_IOT_MODEL = os.path.join(DEFAULT_MODEL_DIR, "iot_model")
PATH_SHORT_TERM = os.path.join(DEFAULT_MODEL_DIR, "short_term_models")

# Ensure MODEL_DIR env var is set for older code expecting it
os.environ.setdefault("MODEL_DIR", DEFAULT_MODEL_DIR)


def local_path(*parts):
    """Return a local filesystem path from relative model parts."""
    return os.path.join(DEFAULT_MODEL_DIR, *parts)
