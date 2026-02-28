"""
Trading Partner Client für Alphaflow

Ermöglicht das Abrufen und Suchen von Trading Partners.
"""

import logging
from typing import Optional, List, Dict, Any
from .dvelop_client import AlphaflowDvelopClient


class TradingPartner:
    """Repräsentiert einen Trading Partner"""

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.number = data.get('number')
        self.name = data.get('name')
        self.company_name = data.get('companyName')
        self.type = data.get('type')
        self.raw_data = data

    def __repr__(self):
        return f"TradingPartner(id={self.id}, number={self.number}, name={self.name})"


class TradingPartnerClient:
    """
    Client zum Abrufen und Suchen von Trading Partners aus Alphaflow.
    """

    def __init__(self, dvelop_client: AlphaflowDvelopClient, organization_id: str):
        """
        Initialisiert den Trading Partner Client.

        Args:
            dvelop_client: Authentifizierter d.velop Client
            organization_id: Alphaflow Organization ID
        """
        self.dvelop_client = dvelop_client
        self.organization_id = organization_id
        self.logger = logging.getLogger(self.__class__.__name__)

        # Trading Partner Endpoint
        self.endpoint = "alphaflow-tradingpartner/tradingpartnerservice/tradingpartners"

    def list_trading_partners(self, limit: int = 1000) -> List[TradingPartner]:
        """
        Holt alle Trading Partners.

        Args:
            limit: Maximum Anzahl der Trading Partners (Standard: 1000)

        Returns:
            Liste von TradingPartner-Objekten
        """
        try:
            self.logger.debug(f"Fetching trading partners from {self.endpoint}")

            params = {
                'i18n': 'true',
                'continue': 'true',
                'count': limit,
                'start': 0
            }

            response = self.dvelop_client.get(self.endpoint, params=params)

            if not response:
                self.logger.warning("No response from trading partner endpoint")
                return []

            # Response kann verschiedene Formate haben
            # Versuche items, data, tradingPartners oder direkt die Liste
            if isinstance(response, dict):
                items = (response.get('items') or
                        response.get('data') or
                        response.get('tradingPartners') or
                        response.get('tradingpartners', []))
            elif isinstance(response, list):
                items = response
            else:
                self.logger.warning(f"Unexpected response format: {type(response)}")
                return []

            trading_partners = [TradingPartner(item) for item in items]
            self.logger.info(f"Found {len(trading_partners)} trading partners")

            return trading_partners

        except Exception as e:
            self.logger.error(f"Failed to fetch trading partners: {e}")
            raise

    def get_by_number(self, number: str) -> Optional[TradingPartner]:
        """
        Sucht einen Trading Partner anhand der Number.

        Args:
            number: Trading Partner Number (z.B. "10001")

        Returns:
            TradingPartner-Objekt oder None wenn nicht gefunden
        """
        try:
            self.logger.debug(f"Searching trading partner by number: {number}")

            # Verwende Filter-Parameter für effiziente Suche
            params = {
                'i18n': 'true',
                'continue': 'true',
                'count': 10,
                'start': 0,
                'filter[number]': str(number)
            }

            response = self.dvelop_client.get(self.endpoint, params=params)

            if not response:
                self.logger.warning(f"No response from trading partner endpoint")
                return None

            # Response verarbeiten
            if isinstance(response, dict):
                items = (response.get('items') or
                        response.get('data') or
                        response.get('tradingPartners') or
                        response.get('tradingpartners', []))
            elif isinstance(response, list):
                items = response
            else:
                self.logger.warning(f"Unexpected response format: {type(response)}")
                return None

            # Finde exakte Übereinstimmung
            for item in items:
                tp = TradingPartner(item)
                if tp.number == str(number):
                    self.logger.info(f"Found trading partner: {tp}")
                    return tp

            self.logger.warning(f"No trading partner found with number: {number}")
            return None

        except Exception as e:
            self.logger.error(f"Failed to find trading partner by number {number}: {e}")
            raise

    def get_by_id(self, trading_partner_id: str) -> Optional[TradingPartner]:
        """
        Holt einen Trading Partner anhand der ID.

        Args:
            trading_partner_id: Trading Partner ID

        Returns:
            TradingPartner-Objekt oder None wenn nicht gefunden
        """
        try:
            endpoint = f"{self.endpoint}/{trading_partner_id}"
            response = self.dvelop_client.get(endpoint)

            if response:
                return TradingPartner(response)

            return None

        except Exception as e:
            self.logger.error(f"Failed to get trading partner {trading_partner_id}: {e}")
            return None

    def search_by_name(self, name: str) -> List[TradingPartner]:
        """
        Sucht Trading Partners nach Name.

        Args:
            name: Suchstring für den Namen

        Returns:
            Liste von passenden TradingPartner-Objekten
        """
        try:
            trading_partners = self.list_trading_partners()

            # Case-insensitive Suche
            search_term = name.lower()
            matches = [
                tp for tp in trading_partners
                if (tp.name and search_term in tp.name.lower()) or
                   (tp.company_name and search_term in tp.company_name.lower())
            ]

            self.logger.info(f"Found {len(matches)} trading partners matching '{name}'")
            return matches

        except Exception as e:
            self.logger.error(f"Failed to search trading partners by name '{name}': {e}")
            raise

    def resolve_number_to_id(self, number: str) -> Optional[str]:
        """
        Convenience-Methode: Löst eine Trading Partner Number zu einer ID auf.

        Args:
            number: Trading Partner Number

        Returns:
            Trading Partner ID oder None wenn nicht gefunden
        """
        tp = self.get_by_number(number)
        return tp.id if tp else None
