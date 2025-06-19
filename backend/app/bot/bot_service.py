from app.common.iservice import IService
import threading

class BotService(IService):
    def __init__(self):
        self._threads = []
        self._running = False

    def start(self) -> None:
        from .bot import bot, check_for_inactive_users, start_config_watcher, logger
        if self._running:
            logger.info("BotService already running.")
            return
        logger.info("Starting BotService...")
        t1 = threading.Thread(target=check_for_inactive_users, daemon=True)
        t1.start()
        self._threads.append(t1)
        start_config_watcher()
        bot.router.observers["pool"] = bot.router.poll_update_message
        t2 = threading.Thread(target=bot.run_forever, daemon=True)
        t2.start()
        self._threads.append(t2)
        self._running = True

    def stop(self) -> None:
        from .bot import logger
        logger.info("Stopping BotService...")
        # There is no direct stop for bot.run_forever, so you may need to implement a stop flag in your bot logic.
        self._running = False
        # Optionally join threads if you add stop logic to your bot
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=1)