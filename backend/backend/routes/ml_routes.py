# backend/backend/routes/ml_routes.py

from flask import Blueprint, jsonify, request
import os
import json
import joblib
from typing import List

import numpy as np
import pandas as pd

from model_fetcher import load_joblib
from model_paths import PATH_OTHER_MODELS, local_path

ml_bp = Blueprint("ml_bp", __name__)

# Debugging path
MODEL_ROOT = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "models"))
MODEL_DIR = PATH_OTHER_MODELS  # local path string

print(f"[DEBUG] Loading ML models from: {MODEL_DIR}")


def _local_exists(fname: str) -> bool:
    return os.path.exists(os.path.join(MODEL_DIR, fname))


def safe_load_model(fname: str):
    """
    Try load locally if present (fast), otherwise try model_fetcher (supabase).
    Returns None on failure.
    """
    local_candidate = os.path.join(MODEL_DIR, fname)
    if os.path.exists(local_candidate):
        try:
            return joblib.load(local_candidate)
        except Exception as e:
            print(f"[WARN] Local joblib load failed for {local_candidate}: {e}")

    # remote attempt via model_fetcher (path relative to models root)
    try:
        return load_joblib(f"other_models/{fname}")
    except Exception as e:
        print(f"[WARN] Remote load failed for other_models/{fname}: {e}")
        return None


def load_feature_list() -> List[str]:
    """
    Load the feature list used by the ML models.
    Order of attempts:
      1) local JSON (regressor_feature_list.json)
      2) local/joblib
      3) remote via load_joblib("other_models/...")
      4) inspect loaded joblib models for feature_names_in_
    """
    candidates_local = [
        os.path.join(MODEL_DIR, "regressor_feature_list.json"),
        os.path.join(MODEL_DIR, "feature_list.joblib"),
        os.path.join(MODEL_DIR, "regressor_feature_list.joblib"),
    ]

    for c in candidates_local:
        if os.path.exists(c):
            try:
                if c.endswith(".json"):
                    with open(c, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
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

    # try remote joblib
    remote_candidates = [
        "other_models/feature_list.joblib",
        "other_models/regressor_feature_list.joblib"
    ]
    for rc in remote_candidates:
        try:
            data = load_joblib(rc)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "features" in data:
                return data["features"]
        except Exception:
            continue

    # inspect model files in local folder (if exists) to find feature_names_in_
    try:
        if os.path.isdir(MODEL_DIR):
            fallback_files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".joblib")]
            for f in fallback_files:
                try:
                    obj = joblib.load(os.path.join(MODEL_DIR, f))
                    feat = getattr(obj, "feature_names_in_", None)
                    if feat is not None:
                        return list(feat)
                except Exception:
                    continue
    except Exception:
        pass

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


def prepare_input(df: pd.DataFrame, expected_features: List[str]) -> np.ndarray:
    if not expected_features:
        return df.values

    df_copy = df.copy()
    for feat in expected_features:
        if feat not in df_copy.columns:
            df_copy[feat] = 0.0

    df_copy = df_copy[expected_features]
    return df_copy.values


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
