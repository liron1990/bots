from flask import jsonify, request
from users.users import Users
from app.webapp.admin.admin_api import admin_api, admin_required

@admin_api.route("/api/admin/users", methods=["GET"])
@admin_required 
def admin_list_users_data():
    users = Users()
    users_data = users.get_users_data()
    return jsonify(users_data)

@admin_api.route("/api/admin/users", methods=["POST"])
@admin_required
def admin_update_user():
    users = Users()
    try:
        data = request.get_json()
        users.update_users_data(data)
        return jsonify({"message": "Users data updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400    

@admin_api.route("/api/admin/users_schema", methods=["GET"])
@admin_required 
def admin_list_schema():
    users = Users()
    users_schema = users.get_users_schema()
    return jsonify(users_schema)


@admin_api.route("/api/admin/users/list", methods=["GET"])
@admin_required
def list_users_names():
    users = Users()
    return jsonify(users.get_users_list())

@admin_api.route("/api/admin/users/<user_name>", methods=["GET"])
@admin_required
def get_user_services(user_name):
    users = Users()
    try:
        return jsonify(users.get_services(user_name))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@admin_api.route("/api/admin/users/<user_name>/enable", methods=["POST"])
@admin_required
def enable_user(user_name):
    users = Users()
    try:
        users.enable_user(user_name)
        return jsonify({"message": f"{user_name} enabled."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@admin_api.route("/api/admin/users/<user_name>/disable", methods=["POST"])
@admin_required
def disable_user(user_name):
    users = Users()
    try:
        users.disable_user(user_name)
        return jsonify({"message": f"{user_name} disabled."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@admin_api.route("/api/admin/users/<user_name>/services/<service_name>/enable", methods=["POST"])
@admin_required
def enable_service(user_name, service_name):
    users = Users()
    try:
        users.enable_service(user_name, service_name)
        return jsonify({"message": f"Service '{service_name}' enabled for {user_name}."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@admin_api.route("/api/admin/users/<user_name>/services/<service_name>/disable", methods=["POST"])
@admin_required
def disable_service(user_name, service_name):
    users = Users()
    try:
        users.disable_service(user_name, service_name)
        return jsonify({"message": f"Service '{service_name}' disabled for {user_name}."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    
@admin_api.route("/api/admin/add_user", methods=["POST"])
@admin_required
def add_user():
    data = request.get_json()
    user_name = data.get("name")
    admin = data.get("admin", False)

    if not user_name:
        return jsonify({"error": "Missing 'name'"}), 400

    try:
        users = Users()
        guid = users.add_user(user_name, admin)
        return jsonify({"message": f"User '{user_name}' added", "guid": guid})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@admin_api.route("/api/admin/users/<user_name>/services", methods=["POST"])
@admin_required
def add_service_to_user(user_name):
    data = request.get_json()
    service_name = data.get("service")
    active = data.get("active", False)

    if not service_name:
        return jsonify({"error": "Missing 'service' name"}), 400

    try:
        users = Users()
        users.add_service_to_user(user_name, service_name, active)
        return jsonify({"message": f"Service '{service_name}' added to user '{user_name}'"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


