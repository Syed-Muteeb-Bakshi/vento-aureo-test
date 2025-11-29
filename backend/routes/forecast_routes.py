# backend/backend/routes/forecast_routes.py

# ============================================================================
# THIS FILE IS DISABLED — FORECAST ROUTES NOW USE EXTERNAL ML SERVER
# See hybrid_routes.py, prophet_routes.py, short_term_routes.py
# Old local model loading is removed.
# ============================================================================

# All functional code has been removed to prevent model_loader imports
# This file now only exports an inert blueprint for safety

from flask import Blueprint

# Create an inert blueprint that does nothing (for safety)
forecast_bp = Blueprint("forecast", __name__)

# No routes registered - blueprint is inert
# This prevents import errors if something tries to import forecast_bp
