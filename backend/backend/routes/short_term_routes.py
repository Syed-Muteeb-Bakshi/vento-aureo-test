# backend/backend/routes/short_term_routes.py

from flask import Blueprint, jsonify, request
from utils.short_term_utils import generate_short_term_forecast

short_term_bp = Blueprint("short_term_bp", __name__)

@short_term_bp.route("/short_term/<city>")
def short_term(city):
    base = request.args.get("base", None)
    try:
        base = float(base) if base else 150.0
    except:
        base = 150.0

    data = generate_short_term_forecast(city, base)
    return jsonify({
        "city": city,
        "base_aqi": base,
        "forecast": data
    })
