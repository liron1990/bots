from whatsapp_api_client_python import API

class GreenApiFactory:
    @staticmethod
    def create(instance_id: str, token_id: str) -> API.GreenAPI:
        MAGIC_NUMBER = "123456"  # Example magic number, replace as needed
        if str(instance_id) == MAGIC_NUMBER:
            from tests.mock_green_api import create_mock_greenapi
            return create_mock_greenapi(instance_id="test_mock_1", debug_mode=True)
        return API.GreenAPI(instance_id, token_id)