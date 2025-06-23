import requests

class ServicesClient:
    def __init__(self, base_url="http://localhost:5051"):
        self.base_url = base_url
    def list_all_services(self):
        """
        Example output:
        [
            {"user": "the_maze", "service": "bot", "state": "running"},
            {"user": "the_maze", "service": "tor4u", "state": "stopped"},
            {"user": "boti", "service": "bot", "state": "running"}
        ]
        """
        return requests.get(f"{self.base_url}/api/services/all").json()

    def start_service(self, user, service):
        """
        Example output:
        {'success': True, 'message': 'Service started'}
        """
        return requests.post(f"{self.base_url}/api/services/start", json={"user": user, "service": service}).json()

    def stop_service(self, user, service):
        """
        Example output:
        {'success': True, 'message': 'Service stopped'}
        """
        return requests.post(f"{self.base_url}/api/services/stop", json={"user": user, "service": service}).json()

    def restart_service(self, user, service):
        """
        Example output:
        {'success': True, 'message': 'Service stopped; Service started'}
        """
        return requests.post(f"{self.base_url}/api/services/restart", json={"user": user, "service": service}).json()

if __name__ == "__main__":
    client = ServicesClient()
    print("# List all services with state")
    print(client.list_all_services())
    print("# Start a service")
    print(client.start_service("boti", "bot"))
    print("# Stop a service")
    print(client.stop_service("boti", "bot"))
    print("# Restart a service")
    print(client.restart_service("the_maze", "bot"))