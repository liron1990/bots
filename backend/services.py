import signal
import multiprocessing
import threading
import time
from flask import Flask, jsonify, request
from app.common.iservice import IService
from app.common.tor4u.tor4u_service import Tor4YouService
from app.bot.bot_service import BotService
from users.app_config import AppConfig, BotConfig, Tor4uConfig
from app.utils.logger import setup_logger, logger
import logging

shutdown_event = multiprocessing.Event()

# Service registry for management
SERVICE_DEFS = [
    # ("the_maze", "tor4u", Tor4YouService, Tor4uConfig("the_maze")),
    # ("the_maze", "bot", BotService, BotConfig("the_maze")),
    ("boti", "bot", BotService, BotConfig("boti")),
]

# Maps (user, service) -> process
service_processes = {}
service_shutdown_events = {}
service_lock = threading.Lock()

def run_service(service_cls, shutdown_event, app_config):
    logger.info(f"Starting service: {service_cls.__name__}")
    setup_logger(service_cls.__name__, log_dir=app_config.products_path / "logs", level=logging.DEBUG)
    service = service_cls(app_config)
    service.start()
    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()

def start_service(user, service):
    with service_lock:
        key = (user, service)
        # Find service def
        for u, s, cls, config in SERVICE_DEFS:
            if u == user and s == service:
                if key in service_processes and service_processes[key].is_alive():
                    return False, "Service already running"
                shutdown_event = multiprocessing.Event()
                proc = multiprocessing.Process(
                    target=run_service,
                    args=(cls, shutdown_event, config),
                    name=f"{user}-{service}"
                )
                proc.start()
                service_processes[key] = proc
                service_shutdown_events[key] = shutdown_event
                return True, "Service started"
        return False, "Service not found"

def stop_service(user, service):
    with service_lock:
        key = (user, service)
        proc = service_processes.get(key)
        shutdown_event = service_shutdown_events.get(key)
        if proc and proc.is_alive():
            if shutdown_event:
                shutdown_event.set()
                proc.join(timeout=5)
            else:
                proc.terminate()
                proc.join(timeout=5)
            # Clean up after stopping
            service_processes.pop(key, None)
            service_shutdown_events.pop(key, None)
            return True, "Service stopped"
        # Clean up if not running
        service_processes.pop(key, None)
        service_shutdown_events.pop(key, None)
        return False, "Service not running"

def restart_service(user, service):
    stopped, msg = stop_service(user, service)
    started, msg2 = start_service(user, service)
    return started, f"{msg}; {msg2}"

def list_services():
    result = {}
    for user, service, *_ in SERVICE_DEFS:
        result.setdefault(user, []).append(service)
    return result

def get_running_services():
    running = {}
    with service_lock:
        for (user, service), proc in service_processes.items():
            if proc.is_alive():
                running.setdefault(user, []).append(service)
    return running

# Flask API for service management
app = Flask(__name__)

@app.route("/api/services", methods=["GET"])
def api_list_services():
    return jsonify(list_services())

@app.route("/api/services/running", methods=["GET"])
def api_running_services():
    return jsonify(get_running_services())

@app.route("/api/services/start", methods=["POST"])
def api_start_service():
    data = request.json
    user = data.get("user")
    service = data.get("service")
    ok, msg = start_service(user, service)
    return jsonify({"success": ok, "message": msg})

@app.route("/api/services/stop", methods=["POST"])
def api_stop_service():
    data = request.json
    user = data.get("user")
    service = data.get("service")
    ok, msg = stop_service(user, service)
    return jsonify({"success": ok, "message": msg})

@app.route("/api/services/restart", methods=["POST"])
def api_restart_service():
    data = request.json
    user = data.get("user")
    service = data.get("service")
    ok, msg = restart_service(user, service)
    return jsonify({"success": ok, "message": msg})

@app.route("/api/services/all", methods=["GET"])
def api_list_all_services():
    """
    Returns a list of all services with their running state.
    Example response:
    [
        {"user": "the_maze", "service": "bot", "state": "running"},
        {"user": "the_maze", "service": "tor4u", "state": "stopped"},
        {"user": "boti", "service": "bot", "state": "running"}
    ]
    """
    all_services = []
    with service_lock:
        for user, service, *_ in SERVICE_DEFS:
            key = (user, service)
            proc = service_processes.get(key)
            state = "running" if proc and proc.is_alive() else "stopped"
            all_services.append({"user": user, "service": service, "state": state})
    return jsonify(all_services)

def flask_thread():
    app.run(host="localhost", port=5051, debug=False, use_reloader=False)

if __name__ == '__main__':
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    app_config = AppConfig("services")
    setup_logger("services", log_dir=app_config.logs_path)

    # Start Flask API in a separate thread
    threading.Thread(target=flask_thread, daemon=True).start()

    # Start all services at launch
    for user, service, cls, config in SERVICE_DEFS:
        start_service(user, service)

    logger.info("Services started successfully. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Signal all shutdown events for graceful exit
        for event in list(service_shutdown_events.values()):
            event.set()

    # Graceful shutdown
    for proc in list(service_processes.values()):
        if proc.is_alive():
            print(f"Terminating {proc.name}...")
            proc.terminate()
            proc.join()
