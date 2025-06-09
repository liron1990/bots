import signal
import threading
from app.common.iservice import IService
from app.common.tor4u.tor4u_service import Tor4YouService
# from app.bot.bot_service import BotService
from app.common.config_yaml_manager import ConfigYamlManager
from users.app_config import AppConfig


shutdown_event = threading.Event()


def stop_services(services):
    for service in services:
        if isinstance(service, IService):
            service.stop()


def handle_exit(signum, frame):
    print("Stopping services...")
    shutdown_event.set()


if __name__ == '__main__':
    app_config = AppConfig("the_maze")
    config_yaml_manager = ConfigYamlManager(app_config.config_path, app_config.data_yaml_path)
    services = [Tor4YouService(config_yaml_manager)]

    for service in services:
        if isinstance(service, IService):
            service.start()
        else:
            raise TypeError(f"Service {service} does not implement IService interface.")

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("Services started. Press Ctrl+C to stop.")

    try:
        while not shutdown_event.wait(timeout=0.5):
            pass
    except KeyboardInterrupt:
        pass

    stop_services(services)
