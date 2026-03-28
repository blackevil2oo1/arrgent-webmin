class BaseController:
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
