import requests
from typing import Optional, Dict, Any


class MiteAuth:
    def __init__(self, account: str, api_key: str):
        self.account = account
        self.api_key = api_key
        self.base_url = f"https://{account}.mite.de"
    
    def get_headers(self) -> Dict[str, str]:
        return {
            'X-MiteApiKey': self.api_key,
            'User-Agent': 'Mite API Client 1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_url(self, endpoint: str) -> str:
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        return f"{self.base_url}/{endpoint}"
    
    def test_connection(self) -> bool:
        try:
            response = requests.get(
                self.get_url('account.json'),
                headers=self.get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            return False