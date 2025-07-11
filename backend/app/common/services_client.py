import json
import time
import uuid
from users.user_paths import Paths
app_paths = Paths("services", "management", make_dirs=True)

class ServicesServerPathes:
    MANAGEMENT_DIR = app_paths.products_path
    STATE_FILE = MANAGEMENT_DIR / "state.json"
    REQUESTS_DIR = MANAGEMENT_DIR / "requests"
    RESPONSE_DIR = MANAGEMENT_DIR / "responses"

ServicesServerPathes.REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
ServicesServerPathes.RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

class ServicesClient:
    @staticmethod
    def list_all_services():
        """
        Reads state.json for all services and their state.
        Example output:
        [
            {"user": "the_maze", "service": "bot", "state": "running"},
            {"user": "the_maze", "service": "tor4u", "state": "stopped"},
            {"user": "boti", "service": "bot", "state": "running"}
        ]
        """
        if not ServicesServerPathes.STATE_FILE.exists():
            return []
        with  ServicesServerPathes.STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    
    @staticmethod
    def __request_action(action, user, service, timeout=10):
        """
        File-based request: creates a request file in the management/requests directory.
        Waits for the result file and returns the result.
        """
        req_id = uuid.uuid4().hex
        req_file = ServicesServerPathes.REQUESTS_DIR / f"{req_id}.json"
        result_file = ServicesServerPathes.RESPONSE_DIR / f"{req_id}.json"
        req = {"action": action, "user": user, "service": service}
        with req_file.open("w", encoding="utf-8") as f:
            json.dump(req, f, ensure_ascii=False, indent=2)
        # Wait for result file (up to timeout seconds)
        for _ in range(int(timeout * 5)):
            if result_file.exists():
                with result_file.open("r", encoding="utf-8") as f:
                    result = json.load(f)
                result_file.unlink(missing_ok=True)
                return result
            time.sleep(0.2)
        return {"success": False, "message": "Timeout waiting for result"}

    @staticmethod
    def start_service(user, service):
        """
        Example output:
        {'success': True, 'message': 'Service started'}
        """
        return ServicesClient.__request_action("start", user, service)
    
    @staticmethod
    def stop_service(user, service):
        """
        Example output:
        {'success': True, 'message': 'Service stopped'}
        """
        return ServicesClient.__request_action("stop", user, service)
    
    @staticmethod
    def restart_service(user, service):
        """
        Example output:
        {'success': True, 'message': 'Service stopped; Service started'}
        """
        return ServicesClient.__request_action("restart", user, service)

if __name__ == "__main__":
    print("# List all services with state")
    print(ServicesClient.list_all_services())
    print("# Start a service")
    print(ServicesClient.start_service("boti", "bot"))
    print("# Stop a service")
    print(ServicesClient.stop_service("boti", "bot"))
    print("# Restart a service")
    print(ServicesClient.restart_service("the_maze", "bot"))