import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentGenerationConfig:
    """Configuration for invoice document generation"""
    doc_template: str = "609bb93bd152c934f2d7a0b3"
    category: str = "62456b6cfb9b51283472ed35"
    attachment_category: str = "62456b7ffb9b51283472ed36"
    document_join_type: str = "62456b6cfb9b51283472ed35"
    type: str = "PDF"
    store_to_dms: bool = True


@dataclass
class AlphaflowConfig:
    """Konfiguration für die Alphaflow Integration"""
    
    # d.velop Cloud Einstellungen
    dvelop_base_url: str
    dvelop_api_key: str
    
    # Alphaflow Einstellungen
    outgoing_invoice_endpoint: str
    organization_id: str
    
    # Default-Werte für Rechnungen
    default_hourly_rate: float = 190.0
    default_vat_rate: float = 19.0
    default_due_days: int = 30
    default_currency: str = "EUR"
    
    # Benutzer-ID für Rechnungsverantwortlichen
    responsible_administrator_id: str = "78728E3E-4025-4B19-B969-74C64E459A40"
    
    # Default Trading Partner
    default_trading_partner_id: str = "5f438d2fc40da20fc4efc338"

    # Invoice type value (system-specific)
    invoice_type_value: Optional[str] = None

    # Workflow name to start after invoice creation (optional)
    workflow_name: Optional[str] = None

    # Control flow ID to forward the workflow after start (optional)
    # E.g. "Flow_0tuv578" - the BPMN sequence flow ID in the workflow
    workflow_forward_flow_id: Optional[str] = None

    # Blacklist für interne/nicht-abrechenbare Projekte
    project_blacklist: List[str] = None

    # Document generation settings (optional)
    document_generation: Optional[DocumentGenerationConfig] = None

    def __post_init__(self):
        """Initialize document_generation with defaults if not provided"""
        if self.document_generation is None:
            self.document_generation = DocumentGenerationConfig()
    
    @classmethod
    def from_env(cls) -> 'AlphaflowConfig':
        """Erstellt Konfiguration aus Umgebungsvariablen"""
        return cls(
            dvelop_base_url=os.getenv('DVELOP_BASE_URL', 'https://alphaflow-test.d-velop.cloud'),
            dvelop_api_key=os.getenv('DVELOP_API_KEY', ''),
            outgoing_invoice_endpoint='alphaflow-outgoinginvoice/outgoinginvoiceservice/outgoinginvoices',
            organization_id=os.getenv('ALPHAFLOW_ORG_ID', '5f3a530a83809e7e377788a5'),
            default_hourly_rate=float(os.getenv('ALPHAFLOW_DEFAULT_HOURLY_RATE', '190.0')),
            default_vat_rate=float(os.getenv('ALPHAFLOW_DEFAULT_VAT_RATE', '19.0')),
            default_due_days=int(os.getenv('ALPHAFLOW_DEFAULT_DUE_DAYS', '30')),
            default_currency=os.getenv('ALPHAFLOW_DEFAULT_CURRENCY', 'EUR'),
            responsible_administrator_id=os.getenv('ALPHAFLOW_ADMIN_ID', '78728E3E-4025-4B19-B969-74C64E459A40'),
            default_trading_partner_id=os.getenv('ALPHAFLOW_DEFAULT_TRADING_PARTNER', '5f438d2fc40da20fc4efc338')
        )
    
    @classmethod
    def from_airflow_variables(cls, variable_getter) -> 'AlphaflowConfig':
        """Erstellt Konfiguration aus Airflow Variables"""
        import json

        try:
            project_blacklist_str = variable_getter.get('MITE_PROJECT_BLACKLIST', '{}')
            blacklist_data = json.loads(project_blacklist_str)
            # Extrahiere die blacklisted_projects Liste
            project_blacklist = blacklist_data.get('blacklisted_projects', []) if isinstance(blacklist_data, dict) else []
        except (json.JSONDecodeError, Exception):
            project_blacklist = []

        return cls(
            dvelop_base_url=variable_getter.get('DVELOP_BASE_URL', 'https://alphaflow-test.d-velop.cloud'),
            dvelop_api_key=variable_getter.get('DVELOP_API_KEY'),
            outgoing_invoice_endpoint='alphaflow-outgoinginvoice/outgoinginvoiceservice/outgoinginvoices',
            organization_id=variable_getter.get('ALPHAFLOW_ORG_ID', '5f3a530a83809e7e377788a5'),
            default_hourly_rate=float(variable_getter.get('ALPHAFLOW_DEFAULT_HOURLY_RATE', 190.0)),
            default_vat_rate=float(variable_getter.get('ALPHAFLOW_DEFAULT_VAT_RATE', 19.0)),
            default_due_days=int(variable_getter.get('ALPHAFLOW_DEFAULT_DUE_DAYS', 30)),
            default_currency=variable_getter.get('ALPHAFLOW_DEFAULT_CURRENCY', 'EUR'),
            responsible_administrator_id=variable_getter.get('ALPHAFLOW_ADMIN_ID', '78728E3E-4025-4B19-B969-74C64E459A40'),
            default_trading_partner_id=variable_getter.get('ALPHAFLOW_DEFAULT_TRADING_PARTNER', '5f438d2fc40da20fc4efc338'),
            project_blacklist=project_blacklist
        )
    
    def get_trading_partner_for_project(self, project_id: str) -> str:
        """Gibt Trading Partner ID zurück (immer default_trading_partner_id)"""
        return self.default_trading_partner_id
    
    def is_project_blacklisted(self, project_id: str) -> bool:
        """Prüft ob ein Projekt auf der Blacklist steht (nicht abgerechnet werden soll)"""
        if not self.project_blacklist:
            return False
        return str(project_id) in self.project_blacklist
    
    def validate_required_fields(self) -> bool:
        """Validiert dass alle erforderlichen Felder gesetzt sind"""
        required_fields = [
            'dvelop_base_url',
            'dvelop_api_key', 
            'organization_id'
        ]
        
        for field in required_fields:
            if not getattr(self, field):
                return False
        
        return True