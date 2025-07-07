from flask import Blueprint, jsonify, request
from functools import wraps
from .auth import get_user_id_from_request
from app.common.services_client import ServicesClient
from users.users import Users

admin_api = Blueprint("admin_api", __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        users = Users()
        user = get_user_id_from_request()
        if not users.is_admin(user):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

@admin_api.route("/api/admin/ping", methods=["GET"])
@admin_required
def admin_ping():
    return jsonify({"status": "ok", "message": "Admin access granted"})

@admin_api.route("/api/admin/users", methods=["GET"])
@admin_required 
def admin_list_users_data():
    users = Users()
    users_data = users.get_users_data()
    return jsonify(users_data)

@admin_api.route("/api/admin/users", methods=["POST"])
@admin_required
def admin_update_user():
    data = request.json
    users = Users()
    users.update_users_data(data)
    return jsonify({"status": "ok", "message": "User data updated successfully"})
    

@admin_api.route("/api/admin/users_schema", methods=["GET"])
@admin_required 
def admin_list_schema():
    users = Users()
    users_schema = users.get_users_schema()
    return jsonify(users_schema)

@admin_api.route("/api/admin/services/all", methods=["GET"])
@admin_required
def admin_list_all_services():
    return jsonify(ServicesClient.list_all_services())

@admin_api.route("/api/admin/services/<action>", methods=["POST"])
@admin_required
def admin_service_action(action):
    if action not in ("start", "stop", "restart"):
        return jsonify({"error": "Invalid action"}), 400
    data = request.json
    user = data.get("user")
    service = data.get("service")
    if action == "start":
        result = ServicesClient.start_service(user, service)
    elif action == "stop":
        result = ServicesClient.stop_service(user, service)
    elif action == "restart":
        result = ServicesClient.restart_service(user, service)
    else:
        result = {"error": "Unknown action"}
    return jsonify(result)