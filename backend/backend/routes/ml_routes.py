from flask import Blueprint, jsonify, request
import os, joblib, json
import numpy as np
import pandas as pd
from typing import List

ml_bp = Blueprint("ml_bp", __name__)

# ===============================
# FIXED MODEL LOADING (UNIVERSAL)
# ===============================
MODEL_ROOT = os.environ.get("MODEL_DIR", "models")
MODEL_DIR = os.path.join(MODEL_ROOT, "other models")

print(f"[DEBUG] Loading ML models from: {MODEL_DIR}")


# -------------------------
# Utilities: load models and feature list
# -------------------------
def safe_load_model(fname):
    p = os.path.join(MODEL_DIR, fname)
    if os.path.exists(p):
        try:
            obj = joblib.load(p)
            print(f"[INFO] Loaded model: {fname}")
            return obj
        except Exception as e:
            print(f"[ERROR] Failed to load {fname}: {e}")
            return None
    else:
        print(f"[WARN] Missing model: {fname}")
        return None

def load_feature_list() -> List[str]:
    # Prefer JSON, then joblib, then fallback to model.feature_names_in_
    candidates = [
        os.path.join(MODEL_DIR, "regressor_feature_list.json"),
        os.path.join(MODEL_DIR, "feature_list.joblib"),
        os.path.join(MODEL_DIR, "regressor_feature_list.joblib"),
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                if c.endswith(".json"):
                    with open(c, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Expect a list, or a dict { "features": [...] }
                    if isinstance(data, dict) and "features" in data:
                        return data["features"]
                    if isinstance(data, list):
                        return data
                else:
                    data = joblib.load(c)
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "features" in data:
                        return data["features"]
            except Exception as e:
                print(f"[WARN] Could not load feature list from {c}: {e}")
    # As last resort, try to inspect a loaded model for `feature_names_in_`
    # (some sklearn models/store pipelines include this)
    fallback_files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".joblib")]
    for f in fallback_files:
        try:
            obj = joblib.load(os.path.join(MODEL_DIR, f))
            feat = getattr(obj, "feature_names_in_", None)
            if feat is not None:
                return list(feat)
        except Exception:
            continue
    # If nothing found, return empty and callers must handle
    return []

# -------------------------
# Load models (safely)
# -------------------------
xgb_model = safe_load_model("xgboost_aqi_model.joblib")
rf_model = safe_load_model("rf_tuned.joblib") or safe_load_model("best_AQI_classifier_Random_Forest.joblib")
aqi_classifier = safe_load_model("xgboost_aqi_category_classifier.joblib")
scaler = safe_load_model("scaler.joblib") or safe_load_model("scaler_regressor.joblib")
imputer = safe_load_model("imputer_regressor.joblib") or safe_load_model("imputer.joblib")

FEATURES = load_feature_list()
print(f"[DEBUG] Loaded feature list with {len(FEATURES)} features.")

# -------------------------
# Helper: prepare input to match expected features
# -------------------------
def prepare_input(df: pd.DataFrame, expected_features: List[str]) -> np.ndarray:
    """
    Ensure df contains exactly expected_features in the same order.
    Missing features are filled with 0. Extra columns are ignored.
    Returns numpy array suitable for pipeline.predict/transform.
    """
    if not expected_features:
        # fallback: use df columns order and return values (best effort)
        return df.values

    # create a copy to avoid changing original
    df_copy = df.copy()

    # Fill missing columns with 0
    for feat in expected_features:
        if feat not in df_copy.columns:
            df_copy[feat] = 0.0

    # Reorder columns
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

        # Accept dict or list-of-dicts; wrap single dict
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame(data)

        # Prepare input based on FEATURE list (fallbacks inside)
        X = prepare_input(df, FEATURES)

        # Apply imputer/scaler if available
        if imputer is not None:
            try:
                X = imputer.transform(X)
            except Exception as e:
                # If imputer expects DataFrame columns, try passing df prepared again
                print("[WARN] Imputer transform failed:", e)
        if scaler is not None:
            try:
                X = scaler.transform(X)
            except Exception as e:
                print("[WARN] Scaler transform failed:", e)

        # Try XGBoost then RF
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
