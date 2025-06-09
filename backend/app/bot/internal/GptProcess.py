from contextlib import AbstractContextManager
from threading import Lock

class GPTProcessingContext(AbstractContextManager):
    _waiting_chats = set()
    _lock = Lock()

    def __init__(self, chat_id: str):
        self.chat_id = chat_id

    def __enter__(self):
        with GPTProcessingContext._lock:
            GPTProcessingContext._waiting_chats.add(self.chat_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with GPTProcessingContext._lock:
            GPTProcessingContext._waiting_chats.discard(self.chat_id)

    @staticmethod
    def is_waiting(chat_id: str) -> bool:
        with GPTProcessingContext._lock:
            return chat_id in GPTProcessingContext._waiting_chats
