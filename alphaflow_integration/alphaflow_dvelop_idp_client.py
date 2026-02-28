"""
Alphaflow d.velop Identity Provider Client
Handles authentication and session management for d.velop cloud services.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .alphaflow_webservice_util import (
    WebServiceClient,
    RetryConfiguration,
    ResponseParser,
    RequestValidator
)


class AuthenticationStatus(Enum):
    """Status der Authentifizierung"""
    NOT_AUTHENTICATED = "not_authenticated"
    AUTHENTICATED = "authenticated"
    AUTHENTICATION_FAILED = "authentication_failed"
    SESSION_EXPIRED = "session_expired"


@dataclass
class AuthenticationCredentials:
    """Authentifizierungs-Credentials für d.velop IDP"""
    api_key: str
    
    def to_bearer_token(self) -> str:
        """Konvertiert zu Bearer Token Format"""
        return f"Bearer {self.api_key}"


@dataclass
class AuthenticationResponse:
    """Response-Daten der Authentifizierung"""
    session_id: Optional[str]
    status: AuthenticationStatus
    error_message: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Prüft ob Authentifizierung erfolgreich war"""
        return self.status == AuthenticationStatus.AUTHENTICATED


class AuthenticationEndpoints:
    """Endpoints für d.velop IDP Services"""
    LOGIN = "/identityprovider/login"
    LOGOUT = "/identityprovider/logout"
    VALIDATE = "/identityprovider/validate"
    REFRESH = "/identityprovider/refresh"


class DvelopIdentityProviderClient:
    """
    Client für die Authentifizierung bei d.velop Identity Provider Services.
    Verwaltet die Anmeldung und Session-Token für Alphaflow Webservices.
    """
    
    def __init__(
        self,
        base_url: str,
        credentials: AuthenticationCredentials,
        timeout_seconds: int = 30,
        retry_configuration: Optional[RetryConfiguration] = None
    ):
        """
        Initialisiert den IDP Client.
        
        Args:
            base_url: Basis-URL der d.velop Cloud Instanz
            credentials: Authentifizierungs-Credentials
            timeout_seconds: Request-Timeout in Sekunden
            retry_configuration: Konfiguration für Retry-Verhalten
        """
        self._validate_initialization_parameters(base_url)
        
        self.credentials = credentials
        self.web_client = self._create_web_client(
            base_url,
            timeout_seconds,
            retry_configuration
        )
        
        self._authentication_session: Optional[str] = None
        self._authentication_status = AuthenticationStatus.NOT_AUTHENTICATED
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _validate_initialization_parameters(self, base_url: str):
        """Validiert Initialisierungs-Parameter"""
        if not RequestValidator.validate_url(base_url):
            raise ValueError(f"Ungültige URL: {base_url}")
    
    def _create_web_client(
        self,
        base_url: str,
        timeout_seconds: int,
        retry_configuration: Optional[RetryConfiguration]
    ) -> WebServiceClient:
        """Erstellt konfigurierten WebService Client"""
        return WebServiceClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            retry_configuration=retry_configuration or RetryConfiguration(
                maximum_attempts=3,
                initial_delay_seconds=1.0
            )
        )
    
    def authenticate(self) -> AuthenticationResponse:
        """
        Führt die Authentifizierung gegen den Identity Provider durch.
        
        Returns:
            AuthenticationResponse mit Status und Session-Informationen
        """
        self.logger.info("Starte Authentifizierung gegen d.velop IDP")
        
        authentication_headers = self._build_authentication_headers()
        response = self._execute_authentication_request(authentication_headers)
        
        if not response:
            return self._create_failed_authentication_response(
                "Keine Antwort vom Server erhalten"
            )
        
        return self._process_authentication_response(response)
    
    def _build_authentication_headers(self) -> Dict[str, str]:
        """Erstellt Headers für Authentifizierung"""
        return {
            "Authorization": self.credentials.to_bearer_token(),
            "Accept": "application/json"
        }
    
    def _execute_authentication_request(
        self,
        headers: Dict[str, str]
    ) -> Optional[Any]:
        """Führt den Authentifizierungs-Request aus"""
        return self.web_client.get(
            endpoint=AuthenticationEndpoints.LOGIN,
            headers=headers
        )
    
    def _process_authentication_response(self, response: Any) -> AuthenticationResponse:
        """Verarbeitet die Authentifizierungs-Antwort"""
        response_data = ResponseParser.extract_json_safely(response)
        
        if not response_data:
            return self._create_failed_authentication_response(
                "Konnte Response nicht als JSON parsen"
            )
        
        session_id = response_data.get("AuthSessionId")
        
        if session_id:
            return self._handle_successful_authentication(session_id)
        
        return self._handle_missing_session_id(response_data)
    
    def _handle_successful_authentication(self, session_id: str) -> AuthenticationResponse:
        """Verarbeitet erfolgreiche Authentifizierung"""
        self._authentication_session = session_id
        self._authentication_status = AuthenticationStatus.AUTHENTICATED
        self.logger.info("Authentifizierung erfolgreich")
        
        return AuthenticationResponse(
            session_id=session_id,
            status=AuthenticationStatus.AUTHENTICATED
        )
    
    def _handle_missing_session_id(self, response_data: Dict) -> AuthenticationResponse:
        """Behandelt fehlende Session-ID in Response"""
        self.logger.error("AuthSessionId nicht in der Antwort gefunden")
        self.logger.debug(f"Erhaltene Daten: {response_data}")
        
        return self._create_failed_authentication_response(
            "Session-ID fehlt in Server-Antwort"
        )
    
    def _create_failed_authentication_response(
        self,
        error_message: str
    ) -> AuthenticationResponse:
        """Erstellt Response für fehlgeschlagene Authentifizierung"""
        self._authentication_status = AuthenticationStatus.AUTHENTICATION_FAILED
        self.logger.error(f"Authentifizierung fehlgeschlagen: {error_message}")
        
        return AuthenticationResponse(
            session_id=None,
            status=AuthenticationStatus.AUTHENTICATION_FAILED,
            error_message=error_message
        )
    
    def create_authenticated_headers(self) -> Dict[str, str]:
        """
        Erstellt Standard-Headers mit gültiger Session.
        
        Returns:
            Headers mit Authorization-Token
        
        Raises:
            RuntimeError: Wenn keine gültige Session vorhanden
        """
        self._ensure_authenticated_session()
        
        return {
            "Authorization": f"Bearer {self._authentication_session}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _ensure_authenticated_session(self):
        """Stellt sicher, dass eine authentifizierte Session vorhanden ist"""
        if not self.has_valid_session():
            raise RuntimeError(
                "Keine gültige Session. Bitte authenticate() aufrufen."
            )
    
    def has_valid_session(self) -> bool:
        """
        Prüft, ob eine gültige Session vorliegt.
        
        Returns:
            True wenn authentifiziert, False sonst
        """
        return (
            self._authentication_session is not None and
            self._authentication_status == AuthenticationStatus.AUTHENTICATED
        )
    
    def get_session_status(self) -> AuthenticationStatus:
        """Gibt aktuellen Authentication-Status zurück"""
        return self._authentication_status
    
    def get_session_id(self) -> Optional[str]:
        """Gibt aktuelle Session-ID zurück"""
        return self._authentication_session
    
    def terminate_session(self) -> bool:
        """
        Beendet die aktuelle Session sauber.
        
        Returns:
            True bei erfolgreichem Logout
        """
        if not self.has_valid_session():
            self.logger.debug("Keine aktive Session zum Beenden")
            return True
        
        success = self._execute_logout_request()
        self._clear_session_data()
        
        return success
    
    def _execute_logout_request(self) -> bool:
        """Führt Logout-Request aus"""
        try:
            headers = self.create_authenticated_headers()
            response = self.web_client.post(
                endpoint=AuthenticationEndpoints.LOGOUT,
                headers=headers
            )
            
            if response:
                self.logger.info("Logout erfolgreich")
                return True
            
        except Exception as error:
            self.logger.warning(f"Logout-Request fehlgeschlagen: {error}")
        
        return False
    
    def _clear_session_data(self):
        """Löscht Session-Daten"""
        self._authentication_session = None
        self._authentication_status = AuthenticationStatus.NOT_AUTHENTICATED
        self.logger.debug("Session-Daten gelöscht")
    
    def validate_session(self) -> bool:
        """
        Validiert die aktuelle Session gegen den Server.
        
        Returns:
            True wenn Session gültig, False sonst
        """
        if not self.has_valid_session():
            return False
        
        headers = self.create_authenticated_headers()
        response = self.web_client.get(
            endpoint=AuthenticationEndpoints.VALIDATE,
            headers=headers
        )
        
        is_valid = response is not None and response.status_code == 200
        
        if not is_valid:
            self._authentication_status = AuthenticationStatus.SESSION_EXPIRED
            self.logger.warning("Session ist abgelaufen")
        
        return is_valid
    
    def refresh_session(self) -> AuthenticationResponse:
        """
        Erneuert die aktuelle Session.
        
        Returns:
            AuthenticationResponse mit neuer Session
        """
        if not self.has_valid_session():
            return self.authenticate()
        
        headers = self.create_authenticated_headers()
        response = self.web_client.post(
            endpoint=AuthenticationEndpoints.REFRESH,
            headers=headers
        )
        
        if response:
            return self._process_authentication_response(response)
        
        self.logger.warning("Session-Refresh fehlgeschlagen, führe neue Authentifizierung durch")
        return self.authenticate()
    
    def ensure_valid_session(self) -> AuthenticationResponse:
        """
        Stellt sicher, dass eine gültige Session vorhanden ist.
        Erneuert oder erstellt Session bei Bedarf.
        
        Returns:
            AuthenticationResponse mit gültiger Session
        """
        if self.validate_session():
            return AuthenticationResponse(
                session_id=self._authentication_session,
                status=AuthenticationStatus.AUTHENTICATED
            )
        
        return self.refresh_session()
    
    def close(self):
        """Schließt Client und gibt Ressourcen frei"""
        self.terminate_session()
        self.web_client.close_session()
    
    def __enter__(self):
        """Context Manager Entry - authentifiziert automatisch"""
        auth_response = self.authenticate()
        
        if not auth_response.is_successful:
            raise RuntimeError(
                f"Authentifizierung fehlgeschlagen: {auth_response.error_message}"
            )
        
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        """Context Manager Exit - beendet Session"""
        self.close()
        return False


class DvelopServiceClient:
    """
    Convenience-Wrapper für d.velop Service Aufrufe mit automatischer Authentifizierung.
    """
    
    def __init__(self, identity_provider: DvelopIdentityProviderClient):
        """
        Initialisiert Service Client mit IDP Client.
        
        Args:
            identity_provider: Konfigurierter IDP Client
        """
        self.identity_provider = identity_provider
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def execute_authenticated_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **options
    ) -> Optional[Any]:
        """
        Führt authentifizierten Request aus.
        
        Args:
            method: HTTP-Methode
            endpoint: API-Endpoint
            payload: Request-Body
            parameters: Query-Parameter
            **options: Weitere Optionen
        
        Returns:
            Response oder None bei Fehler
        """
        self.identity_provider.ensure_valid_session()
        headers = self.identity_provider.create_authenticated_headers()
        
        return self.identity_provider.web_client.execute_request(
            method=method,
            endpoint=endpoint,
            headers=headers,
            json_payload=payload,
            query_parameters=parameters,
            **options
        )
