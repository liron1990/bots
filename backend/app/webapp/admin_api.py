from flask import Blueprint, jsonify, request
from functools import wraps
from .auth import get_user_id_from_request
from app.common.services_client import ServicesClient

admin_api = Blueprint("admin_api", __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user_id_from_request()
        if user != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

@admin_api.route("/api/admin/ping", methods=["GET"])
@admin_required
def admin_ping():
    return jsonify({"status": "ok", "message": "Admin access granted"})

@admin_api.route("/api/admin/services/all", methods=["GET"])
@admin_required
def admin_list_all_services():
    client = ServicesClient("http://localhost:5051")
    return jsonify(client.list_all_services())

@admin_api.route("/api/admin/services/<action>", methods=["POST"])
@admin_required
def admin_service_action(action):
    if action not in ("start", "stop", "restart"):
        return jsonify({"error": "Invalid action"}), 400
    data = request.json
    user = data.get("user")
    service = data.get("service")
    client = ServicesClient("http://localhost:5051")
    if action == "start":
        result = client.start_service(user, service)
    elif action == "stop":
        result = client.stop_service(user, service)
    elif action == "restart":
        result = client.restart_service(user, service)
    else:
        result = {"error": "Unknown action"}
    return jsonify(result)