"""
Alphaflow WebService Utilities
Allgemeine Utilities für HTTP-Requests und WebService-Kommunikation.
"""

import requests
import logging
import time
from typing import Optional, Dict, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass


class HttpMethod(Enum):
    """HTTP-Methoden für WebService-Calls"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class RetryConfiguration:
    """Konfiguration für Retry-Verhalten"""
    maximum_attempts: int = 3
    initial_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    
    def calculate_delay_for_attempt(self, attempt_number: int) -> float:
        """Berechnet Verzögerung für einen bestimmten Versuch"""
        return self.initial_delay_seconds * (self.backoff_multiplier ** attempt_number)


class WebServiceClient:
    """
    Allgemeiner WebService Client mit Retry-Logik und Fehlerbehandlung.
    Kann für verschiedene Alphaflow Services verwendet werden.
    """
    
    def __init__(
        self, 
        base_url: str, 
        timeout_seconds: int = 30, 
        retry_configuration: Optional[RetryConfiguration] = None
    ):
        """
        Initialisiert den WebService Client.
        
        Args:
            base_url: Basis-URL des WebServices
            timeout_seconds: Request-Timeout in Sekunden
            retry_configuration: Konfiguration für Retry-Verhalten
        """
        self.base_url = self._normalize_base_url(base_url)
        self.timeout_seconds = timeout_seconds
        self.retry_configuration = retry_configuration or RetryConfiguration()
        self.session = self._create_configured_session()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _normalize_base_url(self, url: str) -> str:
        """Normalisiert die Basis-URL"""
        return url.rstrip('/')
    
    def _create_configured_session(self) -> requests.Session:
        """Erstellt und konfiguriert eine HTTP-Session"""
        session = requests.Session()
        session.timeout = self.timeout_seconds
        return session
    
    def execute_request(
        self, 
        method: Union[str, HttpMethod], 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        query_parameters: Optional[Dict[str, Any]] = None,
        **additional_options
    ) -> Optional[requests.Response]:
        """
        Führt einen HTTP-Request mit Retry-Logik aus.
        
        Args:
            method: HTTP-Methode
            endpoint: API-Endpoint
            headers: HTTP-Headers
            json_payload: JSON-Daten für Body
            query_parameters: Query-Parameter
            **additional_options: Weitere Parameter für requests
        
        Returns:
            Response-Objekt oder None bei Fehler
        """
        normalized_method = self._normalize_http_method(method)
        full_url = self._build_full_url(endpoint)
        request_configuration = self._prepare_request_configuration(
            headers, json_payload, query_parameters, additional_options
        )
        
        return self._execute_with_retry(
            normalized_method, 
            full_url, 
            request_configuration
        )
    
    def _normalize_http_method(self, method: Union[str, HttpMethod]) -> str:
        """Normalisiert HTTP-Methode zu String"""
        if isinstance(method, HttpMethod):
            return method.value
        return method.upper()
    
    def _build_full_url(self, endpoint: str) -> str:
        """Erstellt vollständige URL aus Basis und Endpoint"""
        base = self.base_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        return f"{base}/{endpoint}"
    
    def _prepare_request_configuration(
        self,
        headers: Optional[Dict[str, str]],
        json_payload: Optional[Dict[str, Any]],
        query_parameters: Optional[Dict[str, Any]],
        additional_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Bereitet Request-Konfiguration vor"""
        configuration = {
            'headers': headers or {},
            'params': query_parameters,
            **additional_options
        }
        
        if json_payload is not None:
            configuration['json'] = json_payload
            
        return configuration
    
    def _execute_with_retry(
        self,
        method: str,
        url: str,
        request_configuration: Dict[str, Any]
    ) -> Optional[requests.Response]:
        """Führt Request mit konfigurierten Wiederholungen aus"""
        max_attempts = self.retry_configuration.maximum_attempts
        
        for current_attempt in range(max_attempts):
            response = self._attempt_single_request(
                method, url, request_configuration, current_attempt, max_attempts
            )
            
            if response is not None:
                return response
                
            if self._should_retry(current_attempt, max_attempts):
                self._wait_before_retry(current_attempt)
        
        return None
    
    def _attempt_single_request(
        self,
        method: str,
        url: str,
        configuration: Dict[str, Any],
        current_attempt: int,
        max_attempts: int
    ) -> Optional[requests.Response]:
        """Führt einen einzelnen Request-Versuch aus"""
        try:
            self._log_request_attempt(method, url, current_attempt, max_attempts)
            response = self.session.request(method, url, **configuration)
            response.raise_for_status()
            self._log_successful_request(response.status_code)
            return response
            
        except requests.exceptions.RequestException as error:
            self._handle_request_error(error, current_attempt, max_attempts)
            return None
    
    def _should_retry(self, current_attempt: int, max_attempts: int) -> bool:
        """Prüft ob weiterer Versuch gemacht werden soll"""
        return current_attempt < max_attempts - 1
    
    def _wait_before_retry(self, attempt_number: int):
        """Wartet konfigurierte Zeit vor nächstem Versuch"""
        delay = self.retry_configuration.calculate_delay_for_attempt(attempt_number)
        self.logger.debug(f"Warte {delay:.2f} Sekunden vor nächstem Versuch")
        time.sleep(delay)
    
    def _log_request_attempt(self, method: str, url: str, current: int, total: int):
        """Protokolliert Request-Versuch"""
        self.logger.debug(f"{method} {url} (Versuch {current + 1}/{total})")
    
    def _log_successful_request(self, status_code: int):
        """Protokolliert erfolgreichen Request"""
        self.logger.debug(f"Request erfolgreich: {status_code}")
    
    def _handle_request_error(
        self,
        error: requests.exceptions.RequestException,
        current_attempt: int,
        max_attempts: int
    ):
        """Behandelt Request-Fehler"""
        attempt_info = f"(Versuch {current_attempt + 1}/{max_attempts})"
        self.logger.warning(f"Request fehlgeschlagen {attempt_info}: {error}")
        
        if not self._should_retry(current_attempt, max_attempts):
            self._log_final_failure(error, max_attempts)
    
    def _log_final_failure(
        self,
        error: requests.exceptions.RequestException,
        max_attempts: int
    ):
        """Protokolliert endgültigen Fehlschlag"""
        self.logger.error(
            f"Request nach {max_attempts} Versuchen fehlgeschlagen: {error}"
        )
        
        if hasattr(error, 'response') and error.response is not None:
            self.logger.error(f"Antworttext: {error.response.text}")
    
    def get(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **options
    ) -> Optional[requests.Response]:
        """Führt GET-Request aus"""
        return self.execute_request(
            HttpMethod.GET,
            endpoint,
            headers=headers,
            query_parameters=parameters,
            **options
        )
    
    def post(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **options
    ) -> Optional[requests.Response]:
        """Führt POST-Request aus"""
        return self.execute_request(
            HttpMethod.POST,
            endpoint,
            headers=headers,
            json_payload=payload,
            **options
        )
    
    def put(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **options
    ) -> Optional[requests.Response]:
        """Führt PUT-Request aus"""
        return self.execute_request(
            HttpMethod.PUT,
            endpoint,
            headers=headers,
            json_payload=payload,
            **options
        )
    
    def patch(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **options
    ) -> Optional[requests.Response]:
        """Führt PATCH-Request aus"""
        return self.execute_request(
            HttpMethod.PATCH,
            endpoint,
            headers=headers,
            json_payload=payload,
            **options
        )
    
    def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        **options
    ) -> Optional[requests.Response]:
        """Führt DELETE-Request aus"""
        return self.execute_request(
            HttpMethod.DELETE,
            endpoint,
            headers=headers,
            **options
        )
    
    def close_session(self):
        """Schließt HTTP-Session und gibt Ressourcen frei"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Eintritt in Context Manager"""
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        """Austritt aus Context Manager"""
        self.close_session()
        return False


class ResponseParser:
    """Parser für HTTP-Response Objekte"""
    
    @staticmethod
    def extract_json_safely(
        response: Optional[requests.Response],
        default_value: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extrahiert JSON-Daten aus Response mit Fehlerbehandlung.
        
        Args:
            response: HTTP-Response Objekt
            default_value: Rückgabewert bei Fehler
        
        Returns:
            Geparste JSON-Daten oder Standardwert
        """
        if not response:
            return default_value
        
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as decode_error:
            ResponseParser._log_json_decode_error(decode_error, response)
            return default_value
    
    @staticmethod
    def _log_json_decode_error(
        error: requests.exceptions.JSONDecodeError,
        response: requests.Response
    ):
        """Protokolliert JSON-Dekodierungsfehler"""
        logger = logging.getLogger('ResponseParser')
        logger.error(f"JSON-Dekodierung fehlgeschlagen: {error}")
        logger.debug(f"Response-Text: {response.text[:500]}")


class ParameterBuilder:
    """Builder für Request-Parameter"""
    
    @staticmethod
    def create_query_parameters(**parameters) -> Dict[str, str]:
        """
        Erstellt Query-Parameter aus Keyword-Argumenten.
        
        Returns:
            Dictionary mit String-Werten, ohne None
        """
        return {
            key: str(value)
            for key, value in parameters.items()
            if value is not None
        }
    
    @staticmethod
    def filter_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entfernt Null-Werte aus Dictionary.
        
        Args:
            data: Zu bereinigendes Dictionary
        
        Returns:
            Dictionary ohne None-Werte
        """
        return {
            key: value
            for key, value in data.items()
            if value is not None
        }


class RequestValidator:
    """Validator für Request-Parameter"""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validiert URL-Format"""
        if not url:
            return False
        return url.startswith(('http://', 'https://'))
    
    @staticmethod
    def validate_timeout(timeout_seconds: int) -> bool:
        """Validiert Timeout-Wert"""
        return 0 < timeout_seconds <= 300
    
    @staticmethod
    def validate_http_method(method: str) -> bool:
        """Validiert HTTP-Methode"""
        valid_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
        return method.upper() in valid_methods
