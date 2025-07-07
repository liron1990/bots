import signal
import multiprocessing
import threading
import time
import json
from app.common.services_client import ServicesServerPathes
from app.common.iservice import IService
from app.common.tor4u.tor4u_service import Tor4YouService
from app.bot.bot_service import BotService
from users.app_config import AppConfig, BotConfig, Tor4uConfig
from app.utils.logger import setup_logger, logger
from users.users import Users
import logging


shutdown_event = multiprocessing.Event()
users = Users()

SERVICE_DEFS = users.get_active_services()

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
            service_processes.pop(key, None)
            service_shutdown_events.pop(key, None)
            return True, "Service stopped"
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

def list_all_services():
    all_services = []
    with service_lock:
        for user, service, *_ in SERVICE_DEFS:
            key = (user, service)
            proc = service_processes.get(key)
            state = "running" if proc and proc.is_alive() else "stopped"
            all_services.append({"user": user, "service": service, "state": state})
    return all_services

def update_state_file():
    """Write the current state to state.json"""
    state = list_all_services()
    with ServicesServerPathes.STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def process_incoming_requests():
    """Process request files in the requests dir."""
    for req_file in ServicesServerPathes.REQUESTS_DIR.glob("*.json"):
        try:
            with req_file.open("r", encoding="utf-8") as f:
                req = json.load(f)
            action = req.get("action")
            user = req.get("user")
            service = req.get("service")
            if action == "start":
                ok, msg = start_service(user, service)
            elif action == "stop":
                ok, msg = stop_service(user, service)
            elif action == "restart":
                ok, msg = restart_service(user, service)
            else:
                ok, msg = False, "Unknown action"
            
            # Write result file
            result_file =  ServicesServerPathes.RESPONSE_DIR / req_file.name
            with result_file.open("w", encoding="utf-8") as rf:
                json.dump({"success": ok, "message": msg}, rf, ensure_ascii=False, indent=2)
        except Exception as e:
            result_file =  ServicesServerPathes.RESPONSE_DIR / req_file.name
            with result_file.open("w", encoding="utf-8") as rf:
                json.dump({"success": False, "message": str(e)}, rf, ensure_ascii=False, indent=2)
        finally:
            req_file.unlink(missing_ok=True)

def management_loop():
    """Background thread to update state and process requests."""
    while True:
        update_state_file()
        process_incoming_requests()
        time.sleep(1)


if __name__ == '__main__':
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    app_config = AppConfig("services")
    setup_logger("services", log_dir=app_config.logs_path)

    # Start management loop in a background thread
    threading.Thread(target=management_loop, daemon=True).start()

    # Start all services at launch
    for user, service, cls, config in SERVICE_DEFS:
        start_service(user, service)

    logger.info("Services started successfully. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for event in list(service_shutdown_events.values()):
            event.set()

    for proc in list(service_processes.values()):
        if proc.is_alive():
            print(f"Terminating {proc.name}...")
            proc.terminate()
            proc.join()
