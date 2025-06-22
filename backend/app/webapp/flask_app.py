from flask import Flask, send_from_directory, jsonify, request
from pathlib import Path
from flask_cors import CORS
import yaml
import os
import json
from app.common.config_yaml_manager import ConfigYamlManager
import atexit
from app.common.tor4u.webhook_handler import WebhookHandler
from users.app_config import AppConfig
from .auth import auth_bp, jwt_required, get_user_id_from_request
from app.utils.logger import setup_logger
import logging

app_config = AppConfig("the_maze", "tor4u")
setup_logger(logger_name="Tor4UWebhook", log_dir=app_config.products_path / "logs", level=logging.DEBUG)

# flask_app = Flask(__name__, static_folder='../../../simple-hebrew-bot-studio/dist')
flask_app = Flask(__name__, static_folder='C:\\projects\\the_maze\\simple-hebrew-bot-studio\\dist')
CORS(flask_app)


def get_user_dir():
    user = get_user_id_from_request()
    if not user:
        return None
    app_config = AppConfig(user, "bot")
    return app_config.config_dir

# Register JWT-based auth routes
flask_app.register_blueprint(auth_bp, url_prefix="/api")


config_yaml_manager = ConfigYamlManager(app_config.config_path, app_config.data_yaml_path)
webhook_handler = WebhookHandler(config_yaml_manager)

@flask_app.route('/webhook_fdw53etvn5ekndfetthg52cc352h97wps5', methods=['POST', 'GET'])
def tor4you_webhook():
    data = request.get_json(silent=True)
    return webhook_handler.handle(data)

@flask_app.route('/api/logout', methods=['POST'])
def logout():
    # Frontend should simply delete the token from storage
    return jsonify({'success': True})

@flask_app.route('/api/protected')
@jwt_required
def protected():
    user = get_user_id_from_request()
    return jsonify({'data': f'Secret data for {user} only'})

@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def serve(path):
    file_path = Path(flask_app.static_folder) / path
    if path != "" and file_path.exists():
        return send_from_directory(flask_app.static_folder, path)
    else:
        return send_from_directory(flask_app.static_folder, 'index.html')

@flask_app.route('/dashboard', methods=['GET'])
@jwt_required
def serve2(path):
    return send_from_directory(flask_app.static_folder, path)

@flask_app.route('/api/bot_messages', methods=['GET'])
@jwt_required
def get_yaml_as_json():
    user_dir = get_user_dir()
    if not user_dir:
        return jsonify({'error': 'Unauthorized'}), 401
    path = user_dir / 'messages.yaml'
    if not path.exists():
        return jsonify({'error': 'File not found'}), 404
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        return jsonify(data)
    except yaml.YAMLError as e:
        return jsonify({'error': str(e)}), 400

from ruamel.yaml import YAML

yaml_ruamel = YAML()
yaml_ruamel.preserve_quotes = True
yaml_ruamel.allow_unicode = True
yaml_ruamel.indent(sequence=4, offset=2)
yaml_ruamel.width = 4096  # prevents breaking long lines

def update_values_only(orig, new):
    if isinstance(orig, dict) and isinstance(new, dict):
        for k in orig:
            if k in new:
                updated_value = update_values_only(orig[k], new[k])
                if updated_value is not None:
                    orig[k] = updated_value
    elif isinstance(orig, list) and isinstance(new, list):
        for i in range(min(len(orig), len(new))):
            updated_value = update_values_only(orig[i], new[i])
            if updated_value is not None:
                orig[i] = updated_value
    else:
        # For scalars, return the new value to be assigned
        return new
    
@flask_app.route('/api/bot_messages', methods=['POST'])
@jwt_required
def update_yaml_from_json():
    user_dir = get_user_dir()
    if not user_dir:
        return jsonify({'error': 'Unauthorized'}), 401
    path = user_dir / 'messages.yaml'
    try:
        
        # original_yaml = yaml.safe_load(path.read_text(encoding='utf-8'))
        with path.open('r', encoding='utf-8') as f:
            original_yaml = yaml_ruamel.load(f)
        new_data = request.json

        # Prevent changes to keys/structure
        def extract_keys(d):
            if isinstance(d, dict):
                return {k: extract_keys(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [extract_keys(v) for v in d]
            return None

        a = extract_keys(original_yaml)
        b = extract_keys(new_data)
        if a != b:
            # Print only the key changes for debugging
            def find_key_changes(a, b, path=""):
                changes = []
                if isinstance(a, dict) and isinstance(b, dict):
                    keys_a = set(a.keys())
                    keys_b = set(b.keys())
                    for k in keys_a - keys_b:
                        changes.append(f"Removed key: {path + '.' if path else ''}{k}")
                    for k in keys_b - keys_a:
                        changes.append(f"Added key: {path + '.' if path else ''}{k}")
                    for k in keys_a & keys_b:
                        changes.extend(find_key_changes(a[k], b[k], f"{path + '.' if path else ''}{k}"))
                elif isinstance(a, list) and isinstance(b, list):
                    # Optionally, compare list lengths or structure
                    if len(a) != len(b):
                        changes.append(f"Changed list length at: {path} ({len(a)} -> {len(b)})")
                    for i, (item_a, item_b) in enumerate(zip(a, b)):
                        changes.extend(find_key_changes(item_a, item_b, f"{path}[{i}]"))
                return changes

            key_changes = find_key_changes(a, b)
            print("Key structure changes detected:")
            for change in key_changes:
                print(change)
            return jsonify({'error': 'Keys/structure cannot be changed.'}), 400

        update_values_only(original_yaml, new_data)

        with path.open('w', encoding='utf-8') as f:
            yaml_ruamel.dump(original_yaml, f)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@flask_app.route('/api/prompt', methods=['GET', 'POST'])
@jwt_required
def prompt_file():
    user_dir = get_user_dir()
    if not user_dir:
        return jsonify({'error': 'Unauthorized'}), 401
    path = user_dir / "prompt.txt"
    if request.method == 'GET':
        if not path.exists():
            return jsonify({'prompt': ''})
        return jsonify({'prompt': path.read_text(encoding='utf-8')})
    else:
        data = request.json
        prompt = data.get('prompt', '')
        path.write_text(prompt, encoding='utf-8')
        return jsonify({'success': True})

@flask_app.route('/api/settings', methods=['GET', 'POST'])
@jwt_required
def user_settings():
    user_dir = get_user_dir()
    if not user_dir:
        return jsonify({'error': 'Unauthorized'}), 401
    path = user_dir / "config.json"
    if request.method == 'GET':
        if not path.exists():
            return jsonify({})
        return jsonify(json.loads(path.read_text(encoding='utf-8')))
    else:
        data = request.json
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return jsonify({'success': True})

@atexit.register
def shutdown():
    config_yaml_manager.stop()
