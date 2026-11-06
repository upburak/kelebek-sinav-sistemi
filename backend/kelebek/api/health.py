"""Local service health endpoint."""

from flask import Blueprint, jsonify


health_api = Blueprint("health", __name__)


@health_api.get("/health")
def health_check():
    """Return a minimal status response without exposing local data paths."""
    return jsonify({"status": "ok", "service": "kelebek-sinav-sistemi"})
