import os
from flask import Blueprint, request, jsonify

upload_bp = Blueprint("upload_bp", __name__)

LOCAL_MODEL_DIR = "/tmp/local_models"
os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)


@upload_bp.route("/upload_model", methods=["POST"])
def upload_model():
    """
    Upload large models (e.g., rf_tuned.joblib) onto Render free-tier.
    Saves to /tmp/local_models which persists until container restart.
    """

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename

    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    save_path = os.path.join(LOCAL_MODEL_DIR, filename)
    file.save(save_path)

    return jsonify({
        "status": "success",
        "message": f"{filename} uploaded successfully",
        "saved_to": save_path
    })
