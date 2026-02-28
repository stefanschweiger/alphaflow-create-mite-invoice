"""
Alphaflow d.velop Client Adapter
Wrapper around the existing d.velop IDP client for easier integration.
"""

import logging
from typing import Optional, Dict, Any
from .alphaflow_dvelop_idp_client import (
    DvelopIdentityProviderClient, 
    DvelopServiceClient,
    AuthenticationCredentials
)
from .alphaflow_webservice_util import RetryConfiguration


class AlphaflowDvelopClient:
    """
    Vereinfachter Wrapper für d.velop Client speziell für Alphaflow Integration.
    """
    
    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 30):
        """
        Initialisiert den Alphaflow d.velop Client.
        
        Args:
            base_url: d.velop Base URL (z.B. https://alphaflow-test.d-velop.cloud)
            api_key: API-Schlüssel für Authentifizierung
            timeout_seconds: Request-Timeout in Sekunden
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Erstelle Credentials
        credentials = AuthenticationCredentials(api_key=api_key)
        
        # Konfiguriere Retry-Behavior
        retry_config = RetryConfiguration(
            maximum_attempts=3,
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0
        )
        
        # Initialisiere IDP Client
        self.idp_client = DvelopIdentityProviderClient(
            base_url=base_url,
            credentials=credentials,
            timeout_seconds=timeout_seconds,
            retry_configuration=retry_config
        )
        
        # Initialisiere Service Client
        self.service_client = DvelopServiceClient(self.idp_client)
        
        self._authenticated = False
        self._session_token = None
    
    def authenticate(self) -> bool:
        """
        Authentifiziert gegen d.velop Identity Provider.
        
        Returns:
            True wenn Authentifizierung erfolgreich, False sonst
        """
        try:
            self.logger.info("Authentifizierung gegen d.velop...")
            response = self.idp_client.authenticate()
            
            if response.is_successful:
                self._authenticated = True
                self._session_token = response.session_id
                self.logger.info("✅ d.velop Authentifizierung erfolgreich")
                return True
            else:
                self.logger.error(f"❌ Authentifizierung fehlgeschlagen: {response.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Fehler bei Authentifizierung: {str(e)}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """
        Stellt sicher, dass eine gültige Authentifizierung vorliegt.
        
        Returns:
            True wenn authentifiziert, False sonst
        """
        if not self._authenticated:
            return self.authenticate()
        
        # Validiere Session
        try:
            if not self.idp_client.validate_session():
                self.logger.info("Session abgelaufen, erneuere Authentifizierung...")
                return self.authenticate()
            return True
        except Exception as e:
            self.logger.warning(f"Session-Validierung fehlgeschlagen: {str(e)}")
            return self.authenticate()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Gibt authentifizierte Headers für API-Requests zurück.
        
        Returns:
            Headers-Dictionary mit Authorization-Token
            
        Raises:
            RuntimeError: Wenn keine gültige Authentifizierung vorliegt
        """
        if not self.ensure_authenticated():
            raise RuntimeError("Authentifizierung fehlgeschlagen")
        
        return self.idp_client.create_authenticated_headers()
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Führt einen authentifizierten GET-Request aus.

        Args:
            endpoint: API-Endpoint (ohne Base-URL)
            params: Query-Parameter

        Returns:
            Response-Daten (JSON-parsed) oder None bei Fehler
        """
        try:
            response = self.service_client.execute_authenticated_request(
                method='GET',
                endpoint=endpoint,
                parameters=params
            )

            if response and response.status_code == 200:
                try:
                    return response.json()
                except Exception as json_err:
                    self.logger.warning(f"Failed to parse JSON response: {json_err}")
                    return None

            return None
        except Exception as e:
            self.logger.error(f"GET-Request fehlgeschlagen: {str(e)}")
            return None
    
    def post(self, endpoint: str, payload: Dict[str, Any], params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
        """
        Führt einen authentifizierten POST-Request aus.

        Args:
            endpoint: API-Endpoint (ohne Base-URL)
            payload: JSON-Payload für Request-Body
            params: Query-Parameter
            headers: Zusätzliche HTTP-Header

        Returns:
            Response-Daten (JSON-parsed) oder None bei Fehler
        """
        try:
            # Prepare kwargs for execute_authenticated_request
            kwargs = {
                'method': 'POST',
                'endpoint': endpoint,
                'payload': payload,
                'parameters': params
            }

            # If additional headers are provided, merge them with auth headers
            if headers:
                # Get auth headers
                auth_headers = self.get_auth_headers()
                # Merge with additional headers (additional headers take precedence)
                merged_headers = {**auth_headers, **headers}
                kwargs['headers'] = merged_headers
                # Use the underlying web_client directly to have full control over headers
                full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
                response = self.idp_client.web_client.execute_request(
                    method='POST',
                    endpoint=endpoint,
                    headers=merged_headers,
                    json_payload=payload,
                    query_parameters=params
                )
            else:
                response = self.service_client.execute_authenticated_request(**kwargs)

            if response and response.status_code in [200, 201]:
                try:
                    return response.json()
                except Exception as json_err:
                    self.logger.warning(f"Failed to parse JSON response: {json_err}")
                    return None

            return None
        except Exception as e:
            self.logger.error(f"POST-Request fehlgeschlagen: {str(e)}")
            return None
    
    def put(self, endpoint: str, payload: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Führt einen authentifizierten PUT-Request aus.

        Args:
            endpoint: API-Endpoint (ohne Base-URL)
            payload: JSON-Payload für Request-Body
            params: Query-Parameter

        Returns:
            Response-Daten (JSON-parsed) oder None bei Fehler
        """
        try:
            response = self.service_client.execute_authenticated_request(
                method='PUT',
                endpoint=endpoint,
                payload=payload,
                parameters=params
            )

            if response and response.status_code in [200, 204]:
                try:
                    return response.json() if response.text else {}
                except Exception as json_err:
                    self.logger.warning(f"Failed to parse JSON response: {json_err}")
                    return {}

            return None
        except Exception as e:
            self.logger.error(f"PUT-Request fehlgeschlagen: {str(e)}")
            return None

    def patch(self, endpoint: str, payload: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Führt einen authentifizierten PATCH-Request aus.

        Args:
            endpoint: API-Endpoint (ohne Base-URL)
            payload: JSON-Payload für Request-Body
            params: Query-Parameter

        Returns:
            Response-Daten (JSON-parsed) oder None bei Fehler
        """
        try:
            response = self.service_client.execute_authenticated_request(
                method='PATCH',
                endpoint=endpoint,
                payload=payload,
                parameters=params
            )

            if response and response.status_code in [200, 204]:
                try:
                    return response.json() if response.text else {}
                except Exception as json_err:
                    self.logger.warning(f"Failed to parse JSON response: {json_err}")
                    return {}

            return None
        except Exception as e:
            self.logger.error(f"PATCH-Request fehlgeschlagen: {str(e)}")
            return None

    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Führt einen authentifizierten DELETE-Request aus.

        Args:
            endpoint: API-Endpoint (ohne Base-URL)
            params: Query-Parameter

        Returns:
            Response-Daten (JSON-parsed) oder None bei Fehler
        """
        try:
            response = self.service_client.execute_authenticated_request(
                method='DELETE',
                endpoint=endpoint,
                parameters=params
            )

            if response and response.status_code in [200, 204]:
                try:
                    return response.json() if response.text else {}
                except Exception as json_err:
                    self.logger.warning(f"Failed to parse JSON response: {json_err}")
                    return {}

            return None
        except Exception as e:
            self.logger.error(f"DELETE-Request fehlgeschlagen: {str(e)}")
            return None
    
    def post_multipart(
        self,
        endpoint: str,
        files: Dict[str, Any],
        data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Führt einen authentifizierten POST-Request mit multipart/form-data aus.

        Args:
            endpoint: API-Endpoint (ohne Base-URL)
            files: Files dictionary für multipart upload
            data: Form data dictionary
            params: Query-Parameter

        Returns:
            Response-Objekt oder None bei Fehler
        """
        try:
            if not self.ensure_authenticated():
                self.logger.error("Authentifizierung fehlgeschlagen")
                return None

            # Get auth headers but remove Content-Type for multipart uploads
            # requests will set the correct multipart/form-data Content-Type automatically
            headers = self.get_auth_headers()
            if 'Content-Type' in headers:
                del headers['Content-Type']

            full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

            # Use the underlying web_client's session
            response = self.idp_client.web_client.session.post(
                full_url,
                headers=headers,
                files=files,
                data=data,
                params=params,
                timeout=self.timeout_seconds
            )

            if response.status_code in [200, 201]:
                return response
            else:
                self.logger.error(
                    f"Multipart POST fehlgeschlagen: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Multipart POST-Request fehlgeschlagen: {str(e)}")
            return None

    def is_authenticated(self) -> bool:
        """Prüft ob Client authentifiziert ist"""
        return self._authenticated and self.idp_client.has_valid_session()

    def get_session_token(self) -> Optional[str]:
        """Gibt aktuellen Session-Token zurück"""
        return self._session_token
    
    def close(self):
        """Schließt Client und beendet Session"""
        if self.idp_client:
            self.idp_client.close()
        self._authenticated = False
        self._session_token = None
    
    def __enter__(self):
        """Context Manager Entry - authentifiziert automatisch"""
        if self.authenticate():
            return self
        else:
            raise RuntimeError("Automatische Authentifizierung fehlgeschlagen")
    
    def __exit__(self, exception_type, exception_value, traceback):
        """Context Manager Exit - schließt Session"""
        self.close()
        return False