import requests
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv

from .auth import MiteAuth
from .endpoints.time_entries import TimeEntriesEndpoint
from .endpoints.projects import ProjectsEndpoint
from .endpoints.customers import CustomersEndpoint
from .endpoints.services import ServicesEndpoint
from .endpoints.users import UsersEndpoint
from .reporting import MonthlyReporter


class MiteClientError(Exception):
    pass


class MiteClient:
    def __init__(self, account: Optional[str] = None, api_key: Optional[str] = None):
        load_dotenv()
        
        self.account = account or os.getenv('MITE_ACCOUNT')
        self.api_key = api_key or os.getenv('MITE_API_KEY')
        
        if not self.account:
            raise MiteClientError("Account name is required. Set MITE_ACCOUNT environment variable or pass account parameter.")
        
        if not self.api_key:
            raise MiteClientError("API key is required. Set MITE_API_KEY environment variable or pass api_key parameter.")
        
        self.auth = MiteAuth(self.account, self.api_key)
        
        # Initialize endpoints
        self.time_entries = TimeEntriesEndpoint(self)
        self.projects = ProjectsEndpoint(self)
        self.customers = CustomersEndpoint(self)
        self.services = ServicesEndpoint(self)
        self.users = UsersEndpoint(self)
        
        # Initialize reporting
        self.reporting = MonthlyReporter(self)
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> requests.Response:
        url = self.auth.get_url(endpoint)
        headers = self.auth.get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )
            
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                if response.status_code == 401:
                    error_msg = "Authentication failed. Check your API key."
                elif response.status_code == 403:
                    error_msg = "Access forbidden. Check your permissions."
                elif response.status_code == 404:
                    error_msg = "Resource not found."
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded. Please try again later."
                
                raise MiteClientError(error_msg)
            
            return response
            
        except requests.exceptions.Timeout:
            raise MiteClientError("Request timeout. Please try again.")
        except requests.exceptions.ConnectionError:
            raise MiteClientError("Connection error. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise MiteClientError(f"Request failed: {str(e)}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        response = self._make_request('GET', endpoint, params=params)
        return response.json()
    
    def post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self._make_request('POST', endpoint, json_data=json_data)
        return response.json() if response.content else {}
    
    def patch(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self._make_request('PATCH', endpoint, json_data=json_data)
        return response.json() if response.content else {}
    
    def delete(self, endpoint: str) -> bool:
        response = self._make_request('DELETE', endpoint)
        return response.status_code in [200, 204]
    
    def test_connection(self) -> bool:
        try:
            self.get('account.json')
            return True
        except MiteClientError:
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        return self.get('account.json')