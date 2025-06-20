import signal
import multiprocessing
from app.common.iservice import IService
from app.common.tor4u.tor4u_service import Tor4YouService
# from users.users_data.boti.bot.bot_service import BotService    
from users.users_programs.boti.bot.bot_service import BotService
from users.app_config import AppConfig
from app.utils.logger import setup_logger, logger
import logging

shutdown_event = multiprocessing.Event()


def run_service(service_cls, shutdown_event, *args):
    logger.info(f"Starting service: {service_cls.__name__}")
    app_config = AppConfig("the_maze")
    setup_logger(service_cls.__name__, log_dir=app_config.products_path / "logs", level=logging.DEBUG)
    service = service_cls(*args)
    service.start()
    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()



if __name__ == '__main__':
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    app_config = AppConfig("services")
    setup_logger("services", log_dir=app_config.logs_path)

    manager = multiprocessing.Manager()
    shutdown_event = manager.Event()

    # Setup signal handlers
    def handle_exit_and_shutdown(signum, frame):
        logger.info("Stopping services...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_exit_and_shutdown)
    signal.signal(signal.SIGTERM, handle_exit_and_shutdown)

    # List of (service class, args)
    service_defs = [
        # (Tor4YouService, ()),
        (BotService, ()),
    ]

    processes = []
    for service_cls, args in service_defs:
        proc = multiprocessing.Process(
            target=run_service,
            args=(service_cls, shutdown_event, *args),
            name=service_cls.__name__
        )
        proc.start()
        processes.append(proc)

    logger.info("Services started successfully. Press Ctrl+C to stop.")

    try:
        while not shutdown_event.wait(timeout=0.5):
            pass
    except KeyboardInterrupt:
        shutdown_event.set()

    # Graceful shutdown
    for proc in processes:
        if proc.is_alive():
            print(f"Terminating {proc.name}...")
            proc.terminate()
            proc.join()
