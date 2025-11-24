# backend/backend/routes/ml_routes.py
from flask import Blueprint, jsonify, request
import os, json
import numpy as np
import pandas as pd
from typing import List
from model_loader import load_joblib

ml_bp = Blueprint("ml_bp", __name__)

# Local path root is still useful for listings
MODEL_ROOT = os.environ.get("MODEL_DIR", "/var/models")
OTHER_PREFIX = "other_models"

def safe_load(fname):
    try:
        return load_joblib(fname, OTHER_PREFIX)
    except Exception:
        print(f"[WARN] Missing model: {fname}")
        return None

print(f"[DEBUG] Loading ML models from GCS bucket (prefix={OTHER_PREFIX})")
xgb_model = safe_load("xgboost_aqi_model.joblib")
rf_model = safe_load("rf_tuned.joblib") or safe_load("best_AQI_classifier_Random_Forest.joblib")
aqi_classifier = safe_load("xgboost_aqi_category_classifier.joblib")
scaler = safe_load("scaler.joblib") or safe_load("scaler_regressor.joblib")
imputer = safe_load("imputer_regressor.joblib") or safe_load("imputer.joblib")

def load_feature_list() -> List[str]:
    # Try JSON or joblib in other_models prefix
    candidates = ["regressor_feature_list.json", "feature_list.joblib", "regressor_feature_list.joblib"]
    for c in candidates:
        try:
            # try joblib first then json
            if c.endswith(".json"):
                data = load_joblib(c, OTHER_PREFIX)  # load_joblib will raise for missing
            else:
                data = load_joblib(c, OTHER_PREFIX)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "features" in data:
                return data["features"]
        except Exception:
            continue
    return []

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
        df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)
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
        df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)
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
