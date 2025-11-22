# backend/backend/routes/ml_routes.py
from flask import Blueprint, jsonify, request
import os, json
import numpy as np
import pandas as pd
from typing import List

from model_loader import load_model, MODEL_CACHE_DIR  # load_model(filename, folder)
import joblib
import requests

ml_bp = Blueprint("ml_bp", __name__)

# -------------------------
# Helpers (feature-list loader)
# -------------------------
MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/tmp/model_cache")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

SUPABASE_PUBLIC_URL = os.environ.get("SUPABASE_PUBLIC_URL")

def _try_load_json_from_supabase(path_suffix: str):
    """Try to fetch a JSON file directly from the public Supabase URL."""
    if not SUPABASE_PUBLIC_URL:
        return None
    url = f"{SUPABASE_PUBLIC_URL}/other_models/{path_suffix}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

def load_feature_list() -> List[str]:
    """
    Resolve the features used by regressors/classifiers.
    Strategy:
      1) Try local repo: backend/backend/models/other_models/regressor_feature_list.json
      2) Try cached file in MODEL_CACHE_DIR
      3) Try fetching from Supabase public URL
      4) Try inspecting any cached joblib model for 'feature_names_in_'
      5) Return []
    """
    # 1) Local file
    base = os.path.dirname(os.path.dirname(__file__))  # backend/backend/routes -> backend/backend
    local_cand = os.path.join(base, "models", "other_models", "regressor_feature_list.json")
    if os.path.exists(local_cand):
        try:
            with open(local_cand, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict) and "features" in data:
                    return data["features"]
                if isinstance(data, list):
                    return data
        except Exception:
            pass

    # 2) Cache file
    cached_json = os.path.join(MODEL_CACHE_DIR, "regressor_feature_list.json")
    if os.path.exists(cached_json):
        try:
            with open(cached_json, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    return data
        except Exception:
            pass

    # 3) Try Supabase public JSON
    sup_data = _try_load_json_from_supabase("regressor_feature_list.json")
    if sup_data:
        if isinstance(sup_data, dict) and "features" in sup_data:
            return sup_data["features"]
        if isinstance(sup_data, list):
            return sup_data

    # 4) Inspect any cached joblib in MODEL_CACHE_DIR for feature_names_in_
    try:
        for f in os.listdir(MODEL_CACHE_DIR):
            if f.endswith(".joblib"):
                p = os.path.join(MODEL_CACHE_DIR, f)
                try:
                    obj = joblib.load(p)
                    feat = getattr(obj, "feature_names_in_", None)
                    if feat is not None:
                        return list(feat)
                except Exception:
                    continue
    except Exception:
        pass

    # 5) Last fallback: empty
    return []

# -------------------------
# Load models (via model_loader)
# -------------------------
def _safe_load_model_filename(fname):
    """Wrap load_model with graceful failure; returns object or None."""
    try:
        return load_model(fname, "other_models")
    except FileNotFoundError:
        print(f"[WARN] Missing model (remote/local): {fname}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load model {fname}: {e}")
        return None

xgb_model = _safe_load_model_filename("xgboost_aqi_model.joblib")
rf_model = _safe_load_model_filename("rf_tuned.joblib") or _safe_load_model_filename("best_AQI_classifier_Random_Forest.joblib")
aqi_classifier = _safe_load_model_filename("xgboost_aqi_category_classifier.joblib")
scaler = _safe_load_model_filename("scaler.joblib") or _safe_load_model_filename("scaler_regressor.joblib")
imputer = _safe_load_model_filename("imputer_regressor.joblib") or _safe_load_model_filename("imputer.joblib")

FEATURES = load_feature_list()
print(f"[DEBUG] Loaded feature list with {len(FEATURES)} features.")

# -------------------------
# Helper: prepare input to match expected features
# -------------------------
def prepare_input(df: pd.DataFrame, expected_features: List[str]) -> np.ndarray:
    if not expected_features:
        return df.values

    df_copy = df.copy()
    for feat in expected_features:
        if feat not in df_copy.columns:
            df_copy[feat] = 0.0
    df_copy = df_copy[expected_features]
    return df_copy.values

# -------------------------
# AQI helpers
# -------------------------
def get_aqi_category(aqi_value):
    if aqi_value <= 50:
        return "Good"
    elif aqi_value <= 100:
        return "Moderate"
    elif aqi_value <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi_value <= 200:
        return "Unhealthy"
    elif aqi_value <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"

# -------------------------
# Routes
# -------------------------
@ml_bp.route("/predict_aqi", methods=["POST"])
def predict_aqi():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided."}), 400

        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame(data)

        X = prepare_input(df, FEATURES)

        # Apply imputer/scaler if available
        if imputer is not None:
            try:
                X = imputer.transform(X)
            except Exception as e:
                print("[WARN] Imputer transform failed:", e)
        if scaler is not None:
            try:
                X = scaler.transform(X)
            except Exception as e:
                print("[WARN] Scaler transform failed:", e)

        model_used = None
        aqi_pred = None
        if xgb_model is not None:
            try:
                aqi_pred = float(xgb_model.predict(X)[0])
                model_used = "XGBoost"
            except Exception as e:
                print("[WARN] xgb predict failed:", e)
        if aqi_pred is None and rf_model is not None:
            try:
                aqi_pred = float(rf_model.predict(X)[0])
                model_used = "RandomForest (fallback)"
            except Exception as e:
                print("[WARN] rf predict failed:", e)

        if aqi_pred is None:
            return jsonify({"error": "No model available or prediction failed."}), 500

        category = get_aqi_category(aqi_pred)
        return jsonify({
            "aqi_predicted": round(aqi_pred, 2),
            "aqi_category": category,
            "model_used": model_used,
            "message": "Prediction successful"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ml_bp.route("/predict_category", methods=["POST"])
def predict_category():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided."}), 400

        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame(data)

        X = prepare_input(df, FEATURES)

        if imputer is not None:
            try:
                X = imputer.transform(X)
            except Exception as e:
                print("[WARN] Imputer transform failed:", e)
        if scaler is not None:
            try:
                X = scaler.transform(X)
            except Exception as e:
                print("[WARN] Scaler transform failed:", e)

        if aqi_classifier is None:
            return jsonify({"error": "Classification model missing."}), 500

        cls_idx = int(aqi_classifier.predict(X)[0])
        categories = ["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous"]
        return jsonify({
            "predicted_category": categories[cls_idx] if cls_idx < len(categories) else "Unknown",
            "model_used": "XGBoost Category Classifier",
            "message": "Category classification successful"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
