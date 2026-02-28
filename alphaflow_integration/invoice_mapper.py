"""
Mite to Alphaflow Invoice Mapper
Konvertiert mite Zeiteinträge in Alphaflow Ausgangsrechnungen.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass

from .config import AlphaflowConfig
from .outgoing_invoice_client import OutgoingInvoiceData, InvoiceItem


@dataclass
class MiteProjectSummary:
    """Zusammenfassung eines mite-Projekts für die Rechnungsstellung"""
    project_id: int
    project_name: str
    customer_id: Optional[int]
    customer_name: str
    total_hours: float
    total_minutes: int
    total_revenue: float
    entries_count: int
    hourly_rate: Optional[float] = None
    
    @classmethod
    def from_summary_dict(cls, summary_dict: Dict[str, Any]) -> 'MiteProjectSummary':
        """Erstellt aus mite Project Summary Dictionary"""
        return cls(
            project_id=summary_dict.get('project_id'),
            project_name=summary_dict.get('project_name', 'Unbekanntes Projekt'),
            customer_id=summary_dict.get('customer_id'),
            customer_name=summary_dict.get('customer_name', 'Unbekannter Kunde'),
            total_hours=summary_dict.get('total_hours', 0.0),
            total_minutes=summary_dict.get('total_minutes', 0),
            total_revenue=summary_dict.get('total_revenue', 0.0),
            entries_count=summary_dict.get('entries_count', 0),
            hourly_rate=None  # Wird später gesetzt
        )


class MiteToInvoiceMapper:
    """
    Mapper für die Konvertierung von mite Daten zu Alphaflow Invoices.
    """
    
    def __init__(self, config: AlphaflowConfig):
        """
        Initialisiert den Mapper.

        Args:
            config: Alphaflow Konfiguration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Standard Unit of Measure ID für Stunden (aus dem Beispiel)
        self.hours_unit_id = "607da1058592fb520cff7451"

    def _extract_buyer_reference(self, project_name: str) -> str:
        """
        Extrahiert die Bestellnummer aus dem Projektnamen.
        Format: "BE24-2001 - Einführung Vertragsmanagement" -> "BE24-2001"

        Args:
            project_name: Name des Projekts

        Returns:
            Bestellnummer oder leerer String wenn nicht gefunden
        """
        if not project_name:
            return ""

        # Suche nach " - " (Leerzeichen-Minus-Leerzeichen) als Trenner
        separator = " - "
        if separator in project_name:
            buyer_reference = project_name.split(separator)[0].strip()
            return buyer_reference

        return ""
    
    def map_project_summaries_to_invoices(
        self, 
        project_summaries: List[Dict[str, Any]], 
        service_period_start: date,
        service_period_end: date,
        invoice_date: Optional[date] = None
    ) -> List[OutgoingInvoiceData]:
        """
        Konvertiert mite Projekt-Zusammenfassungen zu Alphaflow Invoices.
        WICHTIG: Erstellt eine separate Rechnung pro Projekt!
        
        Args:
            project_summaries: Liste der mite Projekt-Zusammenfassungen
            service_period_start: Start des Leistungszeitraums
            service_period_end: Ende des Leistungszeitraums
            invoice_date: Rechnungsdatum (Standard: heute)
            
        Returns:
            Liste von OutgoingInvoiceData Objekten (eine pro Projekt)
        """
        if invoice_date is None:
            invoice_date = date.today()
        
        invoices = []
        
        # Erstelle eine separate Rechnung für jedes Projekt
        blacklisted_projects = []
        for summary in project_summaries:
            project = MiteProjectSummary.from_summary_dict(summary)
            
            try:
                # Prüfe zuerst, ob Projekt auf der Blacklist steht
                if self.config.is_project_blacklisted(str(project.project_id)):
                    blacklisted_projects.append(project.project_name)
                    self.logger.info(f"⚫ Projekt '{project.project_name}' (ID: {project.project_id}) übersprungen - auf Blacklist")
                    continue
                
                # Ermittle Trading Partner ID (mit Fallback auf Default)
                trading_partner_id = self.config.get_trading_partner_for_project(str(project.project_id))
                
                invoice = self._create_invoice_for_project(
                    project=project,
                    trading_partner_id=trading_partner_id,
                    service_period_start=service_period_start,
                    service_period_end=service_period_end,
                    invoice_date=invoice_date
                )
                
                if invoice:
                    invoices.append(invoice)
                    self.logger.info(f"✅ Invoice erstellt für Projekt '{project.project_name}' → Trading Partner {trading_partner_id} ({project.total_hours:.1f}h)")
                
            except Exception as e:
                self.logger.error(f"❌ Fehler bei Invoice-Erstellung für Projekt '{project.project_name}': {str(e)}")
        
        total_processed = len(project_summaries)
        total_blacklisted = len(blacklisted_projects)
        total_invoiced = len(invoices)
        
        self.logger.info(f"Insgesamt {total_invoiced} Invoices erstellt für {total_processed} Projekte")
        if blacklisted_projects:
            self.logger.info(f"⚫ {total_blacklisted} Projekte übersprungen (Blacklist): {', '.join(blacklisted_projects[:3])}")
            if len(blacklisted_projects) > 3:
                self.logger.info(f"   ... und {len(blacklisted_projects) - 3} weitere")
        
        return invoices
    
    def _group_projects_by_trading_partner(self, project_summaries: List[Dict[str, Any]]) -> Dict[str, List[MiteProjectSummary]]:
        """
        Gruppiert Projekte nach Trading Partner ID.
        
        Args:
            project_summaries: Liste der mite Projekt-Zusammenfassungen
            
        Returns:
            Dictionary mit Trading Partner ID als Key und Liste der Projekte als Value
        """
        groups: Dict[str, List[MiteProjectSummary]] = {}
        
        for summary in project_summaries:
            project = MiteProjectSummary.from_summary_dict(summary)
            
            # Ermittle Trading Partner ID über Mapping
            trading_partner_id = self.config.get_trading_partner_for_project(str(project.project_id))
            
            if not trading_partner_id:
                self.logger.warning(f"Keine Trading Partner Zuordnung für Projekt {project.project_name} (ID: {project.project_id})")
                continue
            
            if trading_partner_id not in groups:
                groups[trading_partner_id] = []
            
            groups[trading_partner_id].append(project)
        
        return groups
    
    def _create_invoice_for_project(
        self,
        project: MiteProjectSummary,
        trading_partner_id: str,
        service_period_start: date,
        service_period_end: date,
        invoice_date: date
    ) -> Optional[OutgoingInvoiceData]:
        """
        Erstellt eine Invoice für ein einzelnes Projekt.
        
        Args:
            project: mite Projekt-Zusammenfassung
            trading_partner_id: ID des Trading Partners
            service_period_start: Start des Leistungszeitraums
            service_period_end: Ende des Leistungszeitraums
            invoice_date: Rechnungsdatum
            
        Returns:
            OutgoingInvoiceData oder None bei Fehler
        """
        try:
            # Erstelle Invoice Item für das Projekt
            invoice_item = self._create_invoice_item_from_project(project, 1)
            
            # Extrahiere Bestellnummer aus Projektname
            buyer_reference = self._extract_buyer_reference(project.project_name)

            # Erstelle Invoice
            invoice = OutgoingInvoiceData(
                tradingPartner={"id": trading_partner_id},
                organization={"id": self.config.organization_id},
                responsibleAdministrator={"id": self.config.responsible_administrator_id},
                invoiceItems=[invoice_item],  # Nur ein Item pro Rechnung
                serviceDateStart=service_period_start.strftime('%Y-%m-%d 00:00:00'),
                serviceDateEnd=service_period_end.strftime('%Y-%m-%d 00:00:00'),
                date=invoice_date.strftime('%Y-%m-%d 00:00:00'),
                daysDue=self.config.default_due_days,
                currency=self.config.default_currency,
                remarks=self._generate_invoice_remarks_for_project(project, service_period_start, service_period_end),
                buyerReference=buyer_reference,
                accountingText=f"Consulting {service_period_start.strftime('%Y-%m')} - {project.project_name}",
                invoice_type_value=self.config.invoice_type_value
            )
            
            return invoice
            
        except Exception as e:
            self.logger.error(f"Fehler bei Invoice-Erstellung für Projekt '{project.project_name}': {str(e)}")
            return None
    
    def _create_invoice_for_trading_partner(
        self,
        trading_partner_id: str,
        projects: List[MiteProjectSummary],
        service_period_start: date,
        service_period_end: date,
        invoice_date: date
    ) -> Optional[OutgoingInvoiceData]:
        """
        Erstellt eine Invoice für einen Trading Partner.
        
        Args:
            trading_partner_id: ID des Trading Partners
            projects: Liste der Projekte für diesen Trading Partner
            service_period_start: Start des Leistungszeitraums
            service_period_end: Ende des Leistungszeitraums
            invoice_date: Rechnungsdatum
            
        Returns:
            OutgoingInvoiceData oder None bei Fehler
        """
        try:
            # Erstelle Invoice Items aus Projekten
            invoice_items = []
            for i, project in enumerate(projects, 1):
                item = self._create_invoice_item_from_project(project, i)
                invoice_items.append(item)
            
            # Erstelle Invoice
            invoice = OutgoingInvoiceData(
                tradingPartner={"id": trading_partner_id},
                organization={"id": self.config.organization_id},
                responsibleAdministrator={"id": self.config.responsible_administrator_id},
                invoiceItems=invoice_items,
                serviceDateStart=service_period_start.strftime('%Y-%m-%d 00:00:00'),
                serviceDateEnd=service_period_end.strftime('%Y-%m-%d 00:00:00'),
                date=invoice_date.strftime('%Y-%m-%d 00:00:00'),
                daysDue=self.config.default_due_days,
                currency=self.config.default_currency,
                remarks=self._generate_invoice_remarks(projects, service_period_start, service_period_end),
                buyerReference="",
                accountingText=f"Consulting {service_period_start.strftime('%Y-%m')}",
                invoice_type_value=self.config.invoice_type_value
            )
            
            return invoice
            
        except Exception as e:
            self.logger.error(f"Fehler bei Invoice-Erstellung: {str(e)}")
            return None
    
    def _create_invoice_item_from_project(self, project: MiteProjectSummary, item_number: int) -> InvoiceItem:
        """
        Erstellt ein Invoice Item aus einem mite Projekt.
        
        Args:
            project: mite Projekt-Zusammenfassung
            item_number: Laufende Nummer des Items
            
        Returns:
            InvoiceItem
        """
        # Ermittle Stundensatz
        hourly_rate = project.hourly_rate or self.config.default_hourly_rate
        
        # Berechne Betrag basierend auf tatsächlich abgerechneten Stunden
        # Falls total_revenue verfügbar ist, nutze das, sonst berechne
        # WICHTIG: mite API gibt total_revenue in Cent zurück
        if project.total_revenue and project.total_revenue > 0:
            # total_revenue ist in Cent, konvertiere zu Euro für Stundensatz-Berechnung
            total_revenue_euro = project.total_revenue / 100
            calculated_rate_euro = total_revenue_euro / project.total_hours if project.total_hours > 0 else hourly_rate
            unit_price = calculated_rate_euro
        else:
            unit_price = hourly_rate
        
        return InvoiceItem(
            number=item_number,
            title="Standard-DL-Text",
            description="Dienstleistung gem. Tätigkeitsbericht",
            quantity=project.total_hours,
            unitOfMeasure=self.hours_unit_id,
            unitPrice=unit_price,
            discount=0.0,
            vatRate=self.config.default_vat_rate,
            articleNumber=None,
            costCenter=None,
            glAccount=None
        )
    
    def _generate_item_description(self, project: MiteProjectSummary) -> str:
        """
        Generiert Beschreibung für Invoice Item.
        
        Args:
            project: mite Projekt-Zusammenfassung
            
        Returns:
            Beschreibungstext
        """
        description_parts = [
            f"Projekt: {project.project_name}",
            f"Geleistete Stunden: {project.total_hours}",
            f"Anzahl Einträge: {project.entries_count}"
        ]
        
        if project.customer_name and project.customer_name != project.project_name:
            description_parts.insert(0, f"Kunde: {project.customer_name}")
        
        return " | ".join(description_parts)
    
    def _generate_invoice_remarks(
        self, 
        projects: List[MiteProjectSummary], 
        service_period_start: date,
        service_period_end: date
    ) -> str:
        """
        Generiert Bemerkungen für die Invoice.
        
        Args:
            projects: Liste der Projekte
            service_period_start: Start des Leistungszeitraums
            service_period_end: Ende des Leistungszeitraums
            
        Returns:
            Bemerkungstext
        """
        period_str = f"{service_period_start.strftime('%d.%m.%Y')} - {service_period_end.strftime('%d.%m.%Y')}"
        total_hours = sum(p.total_hours for p in projects)
        
        remarks_parts = [
            f"Beratungsleistungen für den Zeitraum {period_str}",
            f"Gesamtstunden: {total_hours:.1f}h",
            f"Projekte: {', '.join(p.project_name for p in projects[:3])}"  # Max 3 Projektnamen
        ]
        
        if len(projects) > 3:
            remarks_parts[-1] += f" und {len(projects) - 3} weitere"
        
        return " | ".join(remarks_parts)
    
    def _generate_invoice_remarks_for_project(
        self, 
        project: MiteProjectSummary, 
        service_period_start: date,
        service_period_end: date
    ) -> str:
        """
        Generiert Bemerkungen für eine einzelne Projekt-Rechnung.
        
        Args:
            project: mite Projekt-Zusammenfassung
            service_period_start: Start des Leistungszeitraums
            service_period_end: Ende des Leistungszeitraums
            
        Returns:
            Bemerkungstext
        """
        period_str = f"{service_period_start.strftime('%d.%m.%Y')} - {service_period_end.strftime('%d.%m.%Y')}"
        
        remarks_parts = [
            f"Beratungsleistungen für Projekt '{project.project_name}'",
            f"Zeitraum: {period_str}",
            f"Geleistete Stunden: {project.total_hours}h",
            f"Anzahl Buchungen: {project.entries_count}"
        ]
        
        if project.customer_name and project.customer_name != project.project_name:
            remarks_parts.insert(1, f"Kunde: {project.customer_name}")
        
        return " | ".join(remarks_parts)
    
    def validate_project_mappings(self, project_summaries: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[str]]:
        """
        Validiert die Trading Partner Zuordnungen für Projekte und zeigt Blacklist-Status.

        Args:
            project_summaries: Liste der mite Projekt-Zusammenfassungen

        Returns:
            Tuple (explicitly_mapped_projects, default_mapped_projects, blacklisted_projects) mit Listen der Projektnamen
        """
        explicitly_mapped = []
        default_mapped = []
        blacklisted_projects = []

        for summary in project_summaries:
            project = MiteProjectSummary.from_summary_dict(summary)

            # Prüfe zuerst Blacklist-Status
            if self.config.is_project_blacklisted(str(project.project_id)):
                blacklisted_projects.append(f"{project.project_name} (ID: {project.project_id}) - NICHT ABGERECHNET")
                continue

            # Verwendet Default Trading Partner
            default_mapped.append(f"{project.project_name} (ID: {project.project_id}) -> {self.config.default_trading_partner_id} (DEFAULT)")

        return explicitly_mapped, default_mapped, blacklisted_projects
    
    def generate_mapping_template(self, project_summaries: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generiert eine Vorlage für das Projekt-Mapping.
        
        Args:
            project_summaries: Liste der mite Projekt-Zusammenfassungen
            
        Returns:
            Dictionary mit project_id -> "TRADING_PARTNER_ID_HERE"
        """
        mapping_template = {}
        
        for summary in project_summaries:
            project = MiteProjectSummary.from_summary_dict(summary)
            existing_mapping = self.config.get_trading_partner_for_project(str(project.project_id))
            
            if not existing_mapping:
                mapping_template[str(project.project_id)] = f"TRADING_PARTNER_ID_FOR_{project.project_name.upper().replace(' ', '_')}"
        
        return mapping_template