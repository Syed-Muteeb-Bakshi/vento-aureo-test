# backend/backend/routes/ml_routes.py
from flask import Blueprint, jsonify, request
import os, json
import numpy as np
import pandas as pd
from typing import List

from model_loader import load_model  # NEW loader

ml_bp = Blueprint("ml_bp", __name__)

# ===============================
# Model loading
# ===============================
print("[DEBUG] Using MODEL_DIR =", os.environ.get("MODEL_DIR"))

def safe_load_model(filename: str, subfolder: str = "other_models"):
    try:
        model = load_model(filename, subfolder=subfolder)
        print(f"[INFO] Loaded model: {subfolder}/{filename}")
        return model
    except FileNotFoundError:
        print(f"[WARN] Missing model: {subfolder}/{filename}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load {subfolder}/{filename}: {e}")
        return None

# -------------------------
# Load models (safely)
# -------------------------
xgb_model = safe_load_model("xgboost_aqi_model.joblib", "other_models")
rf_model = safe_load_model("rf_tuned.joblib", "other_models") or safe_load_model("best_AQI_classifier_Random_Forest.joblib", "other_models")
aqi_classifier = safe_load_model("xgboost_aqi_category_classifier.joblib", "other_models")
scaler = safe_load_model("scaler.joblib", "other_models") or safe_load_model("scaler_regressor.joblib", "other_models")
imputer = safe_load_model("imputer_regressor.joblib", "other_models") or safe_load_model("imputer.joblib", "other_models")

# -------------------------
# Utilities: load features
# -------------------------
def load_feature_list_from_local_or_models() -> List[str]:
    # prefer JSON/joblib in local MODEL_DIR
    model_root = os.environ.get("MODEL_DIR", "models")
    candidates = [
        os.path.join(model_root, "other_models", "regressor_feature_list.json"),
        os.path.join(model_root, "other_models", "feature_list.joblib"),
        os.path.join(model_root, "other_models", "regressor_feature_list.joblib"),
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                if c.endswith(".json"):
                    with open(c, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "features" in data:
                        return data["features"]
                    if isinstance(data, list):
                        return data
                else:
                    import joblib
                    data = joblib.load(c)
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "features" in data:
                        return data["features"]
            except Exception as e:
                print(f"[WARN] Could not load feature list from {c}: {e}")

    # Fallback: attempt to inspect a joblib model on-disk (local or render)
    try:
        model_dir = os.path.join(model_root, "other_models")
        if os.path.exists(model_dir):
            for f in os.listdir(model_dir):
                if f.endswith(".joblib"):
                    try:
                        obj = load_model(f, subfolder="other_models")
                        feat = getattr(obj, "feature_names_in_", None)
                        if feat is not None:
                            return list(feat)
                    except Exception:
                        continue
    except Exception:
        pass

    return []

FEATURES = load_feature_list_from_local_or_models()
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
