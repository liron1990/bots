from unittest.mock import Mock, MagicMock
import json
import os
import time
import platform
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path
import threading
import uuid
from dataclasses import dataclass, asdict
import tempfile
import atexit
from filelock import FileLock


@dataclass
class CallRecord:
    """Record of a function call"""
    timestamp: str
    method_name: str
    args: list
    kwargs: dict
    process_id: str
    call_id: str
    
    def to_dict(self):
        return asdict(self)


class InterProcessCallTracker:
    """Call tracker that works across processes using file-based storage"""
    
    def __init__(self, mock_instance, storage_dir: str = None, instance_id: str = None):
        self.mock = mock_instance
        self.instance_id = instance_id or str(uuid.uuid4())[:8]
        
        # Use system temp directory for cross-platform compatibility
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(tempfile.gettempdir()) / "greenapi_mock_calls"
        
        self.storage_dir.mkdir(exist_ok=True)
        self.calls_file = self.storage_dir / f"calls_{self.instance_id}.json"
        self.process_id = str(uuid.uuid4())
        self._local_lock = threading.Lock()
        
        # Initialize file if it doesn't exist
        if not self.calls_file.exists():
            self._write_calls([])
        
        # Register cleanup
        atexit.register(self.cleanup)
    
    def _safe_file_operation(self, operation_func, max_retries=5):
        """Safely perform file operations with cross-platform locking"""
        for attempt in range(max_retries):
            try:
                with FileLock(str(self.calls_file) + ".lock"):
                    return operation_func()
            except (TimeoutError, OSError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    time.sleep(0.01 * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    print(f"Warning: File operation failed after {max_retries} attempts: {e}")
                    return None
    
    def _read_calls(self) -> List[CallRecord]:
        """Read all calls from file"""
        def read_operation():
            try:
                if self.calls_file.exists():
                    with open(self.calls_file, 'r') as f:
                        data = json.load(f)
                        return [CallRecord(**call) for call in data]
                return []
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                return []
        
        result = self._safe_file_operation(read_operation)
        return result if result is not None else []
    
    def _write_calls(self, calls: List[CallRecord]):
        """Write all calls to file"""
        def write_operation():
            data = [call.to_dict() for call in calls]
            with open(self.calls_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        self._safe_file_operation(write_operation)
    
    def record_call(self, method_name: str, args: tuple, kwargs: dict):
        """Record a function call"""
        with self._local_lock:
            record = CallRecord(
                timestamp=datetime.now().isoformat(),
                method_name=method_name,
                args=list(args),  # Convert tuple to list for JSON serialization
                kwargs=kwargs,
                process_id=self.process_id,
                call_id=str(uuid.uuid4())
            )
            
            calls = self._read_calls()
            calls.append(record)
            self._write_calls(calls)
    
    def was_called(self, method_path: str) -> bool:
        """Check if a method was called. Use dot notation like 'sending.send_message'"""
        calls = self._read_calls()
        return any(call.method_name == method_path for call in calls)
    
    def call_count(self, method_path: str) -> int:
        """Get call count for a method"""
        calls = self._read_calls()
        return sum(1 for call in calls if call.method_name == method_path)
    
    def get_call_args(self, method_path: str, call_index: int = 0) -> tuple:
        """Get args from specific call"""
        calls = [call for call in self._read_calls() if call.method_name == method_path]
        if call_index < len(calls):
            return tuple(calls[call_index].args)
        return ()
    
    def get_call_kwargs(self, method_path: str, call_index: int = 0) -> dict:
        """Get kwargs from specific call"""
        calls = [call for call in self._read_calls() if call.method_name == method_path]
        if call_index < len(calls):
            return calls[call_index].kwargs
        return {}
    
    def get_all_calls(self, method_path: str = None) -> List[CallRecord]:
        """Get all calls for a method or all calls if no method specified"""
        calls = self._read_calls()
        if method_path:
            return [call for call in calls if call.method_name == method_path]
        return calls
    
    def get_calls_by_process(self, process_id: str = None) -> List[CallRecord]:
        """Get calls from a specific process"""
        calls = self._read_calls()
        target_process = process_id or self.process_id
        return [call for call in calls if call.process_id == target_process]
    
    def reset_calls(self, method_path: str = None):
        """Reset call history for specific method or entire mock"""
        calls = self._read_calls()
        if method_path:
            calls = [call for call in calls if call.method_name != method_path]
        else:
            calls = []
        self._write_calls(calls)
    
    def print_call_summary(self):
        """Print a summary of all calls made"""
        calls = self._read_calls()
        print("=== Inter-Process Mock Call Summary ===")
        
        if not calls:
            print("No calls made")
            return
        
        # Group by method name
        method_calls = {}
        for call in calls:
            if call.method_name not in method_calls:
                method_calls[call.method_name] = []
            method_calls[call.method_name].append(call)
        
        for method_name, call_list in method_calls.items():
            print(f"\n{method_name}: {len(call_list)} call(s)")
            for i, call in enumerate(call_list):
                args_str = ", ".join(repr(arg) for arg in call.args)
                kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in call.kwargs.items())
                params = ", ".join(filter(None, [args_str, kwargs_str]))
                process_info = f"[PID: {call.process_id[:8]}]"
                print(f"  [{i}] {process_info} ({params}) at {call.timestamp}")
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.calls_file.exists():
                os.remove(self.calls_file)
        except (OSError, FileNotFoundError):
            pass


from unittest.mock import MagicMock

class TrackingMagicMock(MagicMock):
    """MagicMock that automatically records calls"""

    def __init__(self, call_tracker, method_path="", *args, **kwargs):
        # הגדר שדות מוקדם כדי לא להפעיל __getattr__
        self.__dict__["call_tracker"] = call_tracker
        self.__dict__["method_path"] = method_path
        super().__init__(*args, **kwargs)

        self.return_value = MagicMock()

    def __call__(self, *args, **kwargs):
        if self.method_path:
            self.call_tracker.record_call(self.method_path, args, kwargs)
        return super().__call__(*args, **kwargs)

    def __getattr__(self, name):
        if name.startswith("_") or name in self.__dict__:
            return super().__getattr__(name)

        child_path = f"{self.method_path}.{name}" if self.method_path else name
        child_mock = TrackingMagicMock(self.call_tracker, child_path)
        setattr(self, name, child_mock)
        return child_mock




class MockGreenApi:
    """Simple dynamic mock for GreenApi that works across processes"""
    
    def __init__(self, 
                 idInstance: str,
                 apiTokenInstance: str,
                 debug_mode: bool = False,
                 raise_errors: bool = False,
                 host: str = "https://api.green-api.com",
                 media: str = "https://media.green-api.com",
                 host_timeout: float = 180,
                 media_timeout: float = 10800,
                 storage_dir: str = None,
                 instance_id: str = None):
        
        # Store init parameters
        self.idInstance = idInstance
        self.apiTokenInstance = apiTokenInstance
        self.debug_mode = debug_mode
        self.raise_errors = raise_errors
        self.host = host
        self.media = media
        self.host_timeout = host_timeout
        self.media_timeout = media_timeout
        
        # Create call tracker that works across processes
        self.call_tracker = InterProcessCallTracker(self, storage_dir, instance_id)
        
        # Create tracking mock objects for all modules
        self.account = TrackingMagicMock(self.call_tracker, "account")
        self.device = TrackingMagicMock(self.call_tracker, "device")
        self.groups = TrackingMagicMock(self.call_tracker, "groups")
        self.journals = TrackingMagicMock(self.call_tracker, "journals")
        self.marking = TrackingMagicMock(self.call_tracker, "marking")
        self.queues = TrackingMagicMock(self.call_tracker, "queues")
        self.receiving = TrackingMagicMock(self.call_tracker, "receiving")
        self.sending = TrackingMagicMock(self.call_tracker, "sending")
        self.serviceMethods = TrackingMagicMock(self.call_tracker, "serviceMethods")
        self.webhooks = TrackingMagicMock(self.call_tracker, "webhooks")
        
        # Create tracking mock methods
        self.request = TrackingMagicMock(self.call_tracker, "request")
        self.raw_request = TrackingMagicMock(self.call_tracker, "raw_request")
        
        # Create mock logger
        self.logger = MagicMock()
    
    def __getattr__(self, name):
        """Dynamically create any missing attributes as tracking mocks"""
        mock_attr = TrackingMagicMock(self.call_tracker, name)
        setattr(self, name, mock_attr)
        return mock_attr


# Convenience functions
def create_mock_greenapi(instance_id: str = None, **kwargs) -> MockGreenApi:
    """Factory function to create a mock GreenApi instance"""
    return MockGreenApi(
        idInstance=kwargs.get('idInstance', 'test_instance'),
        apiTokenInstance=kwargs.get('apiTokenInstance', 'test_token'),
        instance_id=instance_id,
        **{k: v for k, v in kwargs.items() if k not in ['idInstance', 'apiTokenInstance']}
    )


def get_call_tracker(instance_id: str, storage_dir: str = None):
    """Get call tracker for an existing mock instance (for use in different process)"""
    return InterProcessCallTracker(None, storage_dir, instance_id)


# Example usage
if __name__ == "__main__":
    # Create mock instance with specific ID
    mock_api = create_mock_greenapi(instance_id="test_mock_1", debug_mode=True)
    
    # Use the mock
    mock_api.sending.send_message("123456789", "Hello World!")
    mock_api.sending.send_message("987654321", "Hello Again!")
    mock_api.account.get_settings()
    mock_api.groups.create_group("Test Group", ["123", "456"])
    
    # Check calls in same process
    print("=== Same Process ===")
    tracker = mock_api.call_tracker
    print(f"Was send_message called? {tracker.was_called('sending.send_message')}")
    print(f"Call count: {tracker.call_count('sending.send_message')}")
    tracker.print_call_summary()
    
    # Simulate different process - create new tracker with same instance_id
    print("\n=== Different Process Simulation ===")
    other_process_tracker = get_call_tracker("test_mock_1")
    print(f"From other process - was send_message called? {other_process_tracker.was_called('sending.send_message')}")
    print(f"From other process - call count: {other_process_tracker.call_count('sending.send_message')}")
    print(f"From other process - first call args: {other_process_tracker.get_call_args('sending.send_message', 0)}")
    
    # Clean up
    tracker.cleanup()