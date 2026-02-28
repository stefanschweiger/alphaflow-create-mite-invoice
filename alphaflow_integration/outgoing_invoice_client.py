"""
Alphaflow Outgoing Invoice API Client
Spezialisiert auf die Erstellung von Ausgangsrechnungen in der Alphaflow-Plattform.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from .dvelop_client import AlphaflowDvelopClient


@dataclass
class DocumentGenerationResult:
    """Result of document generation operation"""
    success: bool
    document_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class InvoiceItem:
    """Einzelposten einer Rechnung"""
    number: int
    title: str
    description: str
    quantity: float
    unitOfMeasure: str
    unitPrice: float
    discount: float = 0.0
    vatRate: float = 19.0
    articleNumber: Optional[str] = None
    costCenter: Optional[str] = None
    glAccount: Optional[str] = None
    
    @property
    def totalNetAmount(self) -> float:
        """Berechnet Nettobetrag"""
        return round((self.quantity * self.unitPrice) * (1 - self.discount / 100), 2)
    
    @property
    def vatAmount(self) -> float:
        """Berechnet Mehrwertsteuerbetrag"""
        return round(self.totalNetAmount * (self.vatRate / 100), 2)
    
    @property
    def totalAmount(self) -> float:
        """Berechnet Gesamtbetrag inkl. MwSt"""
        return round(self.totalNetAmount + self.vatAmount, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für API"""
        item_dict = {
            'number': self.number,
            'title': self.title,
            'description': self.description,
            'quantity': self.quantity,
            'unitOfMeasure': self.unitOfMeasure,
            'unitPrice': self.unitPrice,
            'discount': self.discount,
            'totalNetAmount': self.totalNetAmount,
            'vatRate': self.vatRate,
            'articleNumber': self.articleNumber,
            'costCenter': self.costCenter,
            'glAccount': self.glAccount,
            'data': None,
            'group': None,
            'id': f"{hash(self.title + str(self.quantity))}"  # Einfache ID-Generierung
        }
        return {k: v for k, v in item_dict.items() if v is not None or k in ['group', 'data']}


@dataclass
class OutgoingInvoiceData:
    """Ausgangsrechnung-Datenstruktur"""
    tradingPartner: Dict[str, Any]
    organization: Dict[str, Any]
    responsibleAdministrator: Dict[str, Any]
    invoiceItems: List[InvoiceItem]
    serviceDateStart: str
    serviceDateEnd: str
    date: str
    daysDue: int = 30
    currency: str = "EUR"
    remarks: str = ""
    buyerReference: str = ""
    accountingText: str = ""
    invoice_type_value: Optional[str] = None
    
    @property
    def totalNetAmount(self) -> float:
        """Berechnet Gesamt-Nettobetrag"""
        return round(sum(item.totalNetAmount for item in self.invoiceItems), 2)
    
    @property
    def totalVatAmount(self) -> float:
        """Berechnet Gesamt-Mehrwertsteuerbetrag"""
        return round(sum(item.vatAmount for item in self.invoiceItems), 2)
    
    @property
    def totalAmount(self) -> float:
        """Berechnet Gesamtbetrag inkl. MwSt"""
        return round(self.totalNetAmount + self.totalVatAmount, 2)
    
    @property
    def dueDate(self) -> str:
        """Berechnet Fälligkeitsdatum"""
        invoice_date = datetime.fromisoformat(self.date.replace(' 00:00:00', ''))
        due_date = invoice_date.replace(day=1)  # Erste des Folgemonats
        if due_date.month == 12:
            due_date = due_date.replace(year=due_date.year + 1, month=1)
        else:
            due_date = due_date.replace(month=due_date.month + 1)
        return due_date.strftime('%Y-%m-%d 00:00:00')
    
    def to_api_format(self) -> Dict[str, Any]:
        """Konvertiert zu API-Format entsprechend dem bereitgestellten Beispiel"""
        # Berechne MwSt-Aufschlüsselung (vereinfacht für 19%)
        vat_amounts = {}
        for item in self.invoiceItems:
            rate = item.vatRate
            if rate not in vat_amounts:
                vat_amounts[rate] = {'net': 0, 'vat': 0, 'total': 0}
            vat_amounts[rate]['net'] += item.totalNetAmount
            vat_amounts[rate]['vat'] += item.vatAmount  
            vat_amounts[rate]['total'] += item.totalAmount
        
        # Nehme die erste/hauptsächliche MwSt-Rate
        main_vat_rate = list(vat_amounts.keys())[0] if vat_amounts else 19.0
        main_amounts = vat_amounts.get(main_vat_rate, {'net': 0, 'vat': 0, 'total': 0})
        
        return {
            "dmsDocumentType": None,
            "dmsDocumentTypeName": None,
            "importCode": None,
            "sealed": False,
            "createdAt": None,
            "creator": None,
            "updatedBy": None,
            "updatedAt": None,
            "deletedAt": None,
            "draftedAt": None,
            "hasDocuments": False,
            "hasComments": False,
            "displayTitle": f"{self.tradingPartner.get('name', 'Unbekannt')} ()",
            "optionTitle": f"{self.tradingPartner.get('name', 'Unbekannt')} ()",
            "accessControlListRead": None,
            "accessControlListWrite": None,
            "accessControlListDelete": None,
            "workflow": None,
            "currentWorkflowResponsibles": "",
            "currentWorkflowResponsibleNames": None,
            "workflowFinishedAt": None,
            "workflowStatus": None,
            "squeezeDocumentIDs": None,
            "type": {
                "name": None,
                "value": self.invoice_type_value if self.invoice_type_value else "INVOICE"
            },
            "tradingPartner": self.tradingPartner,
            "organization": self.organization,
            "responsibleAdministrator": self.responsibleAdministrator,
            "creditInvoice": self._get_empty_credit_invoice(),
            "contract": self._get_empty_contract(),
            "status": {
                "name": None,
                "value": "NEW"
            },
            "paidStatus": {
                "name": None,
                "value": "UNPAID"
            },
            "overdue": False,
            "sendInvoice": False,
            "tradingPartnerContact": self._get_empty_trading_partner_contact(),
            "currency": {
                "name": None,
                "value": self.currency
            },
            "customFields": {},
            "invoiceItems": [item.to_dict() for item in self.invoiceItems],
            "id": "",
            "reminderLevel": "0",
            "serviceDateStart": self.serviceDateStart,
            "serviceDateEnd": self.serviceDateEnd,
            "number": "",
            "date": self.date,
            "firstInvoiceSend": "",
            "paymentDate": "",
            "buyerReference": self.buyerReference,
            "totalNetAmount": self.totalNetAmount,
            "totalVatAmount": self.totalVatAmount,
            "totalAmount": self.totalAmount,
            "netAmount1": main_amounts['net'],
            "vatRate1": main_vat_rate,
            "vatAmount1": main_amounts['vat'],
            "totalAmount1": main_amounts['total'],
            "netAmount2": "",
            "vatRate2": "",
            "vatAmount2": "",
            "totalAmount2": "",
            "netAmount3": "",
            "vatRate3": "",
            "vatAmount3": "",
            "totalAmount3": "",
            "daysDue": self.daysDue,
            "dueDate": self.dueDate,
            "discountDays1": "",
            "discountRate1": "",
            "discountDate1": "",
            "discountDays2": "",
            "discountRate2": "",
            "discountDate2": "",
            "accountingText": self.accountingText,
            "remarks": self.remarks
        }
    
    def _get_empty_credit_invoice(self) -> Dict[str, Any]:
        """Gibt leere Gutschrift-Struktur zurück"""
        return {
            "dmsDocumentType": None,
            "dmsDocumentTypeName": None,
            "importCode": None,
            "sealed": False,
            "createdAt": None,
            "creator": None,
            "updatedBy": None,
            "updatedAt": None,
            "deletedAt": None,
            "draftedAt": None,
            "hasDocuments": False,
            "hasComments": False,
            "displayTitle": None,
            "optionTitle": None,
            "accessControlListRead": None,
            "accessControlListWrite": None,
            "accessControlListDelete": None,
            "workflow": None,
            "currentWorkflowResponsibles": "",
            "currentWorkflowResponsibleNames": None,
            "workflowFinishedAt": None,
            "workflowStatus": None,
            "squeezeDocumentIDs": None,
            "type": None,
            "number": None,
            "tradingPartner": None,
            "organization": None,
            "responsibleAdministrator": None,
            "creditInvoice": None,
            "contract": None,
            "date": None,
            "remarks": None,
            "totalNetAmount": None,
            "totalVatAmount": None,
            "daysDue": None,
            "status": None,
            "paidStatus": {
                "value": None,
                "name": None
            },
            "dueDate": None,
            "overdue": False,
            "totalAmount": None,
            "reminderLevel": 0,
            "sendInvoice": False,
            "firstInvoiceSend": None,
            "paymentDate": None,
            "serviceDateStart": None,
            "serviceDateEnd": None,
            "buyerReference": None,
            "tradingPartnerContact": None,
            "netAmount1": None,
            "netAmount2": None,
            "netAmount3": None,
            "vatRate1": None,
            "vatRate2": None,
            "vatRate3": None,
            "vatAmount1": None,
            "vatAmount2": None,
            "vatAmount3": None,
            "totalAmount1": None,
            "totalAmount2": None,
            "totalAmount3": None,
            "discountDays1": None,
            "discountDays2": None,
            "discountRate1": None,
            "discountRate2": None,
            "discountDate1": None,
            "discountDate2": None,
            "accountingText": None,
            "currency": None,
            "customFields": None,
            "invoiceItems": [],
            "id": None
        }
    
    def _get_empty_contract(self) -> Dict[str, Any]:
        """Gibt leere Vertrag-Struktur zurück"""
        return {
            "dmsDocumentType": None,
            "dmsDocumentTypeName": None,
            "importCode": None,
            "sealed": False,
            "createdAt": None,
            "creator": None,
            "updatedBy": None,
            "updatedAt": None,
            "deletedAt": None,
            "draftedAt": None,
            "hasComments": False,
            "displayTitle": "null (null)",
            "optionTitle": "null (null)",
            "accessControlListRead": None,
            "accessControlListWrite": None,
            "accessControlListDelete": None,
            "workflow": None,
            "currentWorkflowResponsibles": "",
            "currentWorkflowResponsibleNames": None,
            "workflowFinishedAt": None,
            "workflowStatus": None,
            "squeezeDocumentIDs": None,
            "subject": None,
            "tradingPartner": None,
            "contact": None,
            "ownRole": {
                "value": None,
                "name": None
            },
            "organization": None,
            "contractType": None,
            "contractStatus": {
                "value": None,
                "name": None
            },
            "internalNumber": None,
            "externalNumber": None,
            "responsible": None,
            "frameContract": None,
            "relatedFrameContract": None,
            "ownSignature": None,
            "partnerSignature": None,
            "startDate": None,
            "endDate": None,
            "duration": None,
            "terminationReminder": "0",
            "renewalDate": None,
            "followingContractPeriod": None,
            "renewalReminder": "0",
            "terminationValue": None,
            "terminationUnit": {
                "value": None,
                "name": None
            },
            "terminationCalendarEvent": {
                "value": None,
                "name": None
            },
            "firstTermination": None,
            "nextTermination": None,
            "terminationDate": None,
            "terminationBy": {
                "value": None,
                "name": None
            },
            "terminationRemark": None,
            "cancellationReminder": "0",
            "overdueTasks": 0,
            "title": None,
            "typeShortName": None,
            "additionalAccessGranted": "",
            "additionalAccessDenied": "",
            "customFields": None,
            "automaticRenewal": {
                "value": None,
                "name": None
            },
            "riskAnalysis": None,
            "hasDocuments": False,
            "id": None
        }
    
    def _get_empty_trading_partner_contact(self) -> Dict[str, Any]:
        """Gibt leere Trading Partner Contact Struktur zurück"""
        return {
            "dmsDocumentType": None,
            "dmsDocumentTypeName": None,
            "importCode": None,
            "sealed": False,
            "createdAt": None,
            "creator": None,
            "updatedBy": None,
            "updatedAt": None,
            "deletedAt": None,
            "draftedAt": None,
            "hasDocuments": False,
            "hasComments": False,
            "displayTitle": "",
            "optionTitle": "",
            "accessControlListRead": None,
            "accessControlListWrite": None,
            "accessControlListDelete": None,
            "organization": None,
            "number": None,
            "name": None,
            "salutation": None,
            "title": None,
            "firstName": None,
            "tradingPartner": None,
            "jobTitle": None,
            "division": None,
            "type": None,
            "description": None,
            "phone": None,
            "mobilePhone": None,
            "fax": None,
            "email": None,
            "street": None,
            "zip": None,
            "city": None,
            "country": None,
            "region": None,
            "postboxZip": None,
            "postbox": None,
            "addressAnnex": None,
            "displayName": "",
            "active": {
                "value": None,
                "name": None
            },
            "archived": None,
            "id": None
        }


class OutgoingInvoiceClient:
    """Client für Alphaflow Ausgangsrechnungs-API"""
    
    def __init__(self, dvelop_client: AlphaflowDvelopClient, endpoint: str):
        """
        Initialisiert den Invoice Client.
        
        Args:
            dvelop_client: Authentifizierter d.velop Client
            endpoint: API-Endpoint für Ausgangsrechnungen
        """
        self.dvelop_client = dvelop_client
        self.endpoint = endpoint.lstrip('/')
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_invoice(self, invoice_data: OutgoingInvoiceData) -> Optional[Dict[str, Any]]:
        """
        Erstellt eine neue Ausgangsrechnung.
        
        Args:
            invoice_data: Rechnungsdaten
            
        Returns:
            Response-Daten der erstellten Rechnung oder None bei Fehler
        """
        try:
            self.logger.info(f"Erstelle Ausgangsrechnung für {invoice_data.tradingPartner.get('name', 'Unbekannt')}")
            
            # Konvertiere zu API-Format
            api_payload = invoice_data.to_api_format()
            
            # Debug-Output für erste Tests
            self.logger.debug(f"Invoice payload: Nettobetrag={api_payload['totalNetAmount']}, Bruttobetrag={api_payload['totalAmount']}")
            
            # Sende POST-Request
            response = self.dvelop_client.post(
                endpoint=self.endpoint,
                payload=api_payload
            )
            
            if response:
                self.logger.info(f"✅ Rechnung erfolgreich erstellt")
                return response
            else:
                self.logger.error("❌ Fehler beim Erstellen der Rechnung")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Erstellen der Rechnung: {str(e)}")
            return None
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Ruft eine Rechnung anhand der ID ab.
        
        Args:
            invoice_id: ID der Rechnung
            
        Returns:
            Rechnungsdaten oder None bei Fehler
        """
        try:
            endpoint = f"{self.endpoint}/{invoice_id}"
            response = self.dvelop_client.get(endpoint=endpoint)
            return response
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abrufen der Rechnung {invoice_id}: {str(e)}")
            return None
    
    def list_invoices(self, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Listet Rechnungen auf.
        
        Args:
            params: Query-Parameter für Filterung
            
        Returns:
            Liste von Rechnungen oder None bei Fehler
        """
        try:
            response = self.dvelop_client.get(
                endpoint=self.endpoint,
                params=params
            )
            return response if isinstance(response, list) else None
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Auflisten der Rechnungen: {str(e)}")
            return None
    
    def update_invoice(self, invoice_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Aktualisiert eine Rechnung.

        Args:
            invoice_id: ID der Rechnung
            update_data: Zu aktualisierende Daten

        Returns:
            Aktualisierte Rechnungsdaten oder None bei Fehler
        """
        try:
            endpoint = f"{self.endpoint}/{invoice_id}"
            response = self.dvelop_client.patch(
                endpoint=endpoint,
                payload=update_data
            )
            return response
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Aktualisieren der Rechnung {invoice_id}: {str(e)}")
            return None

    def generate_invoice_document(
        self,
        invoice_id: str,
        doc_config: 'DocumentGenerationConfig'
    ) -> DocumentGenerationResult:
        """
        Generates a PDF document for an invoice.

        Args:
            invoice_id: ID of the invoice to generate document for
            doc_config: Document generation configuration

        Returns:
            DocumentGenerationResult with success status and document ID or error
        """
        try:
            payload = {
                "id": invoice_id,
                "docTemplate": doc_config.doc_template,
                "category": doc_config.category,
                "type": doc_config.type,
                "freeText": "",
                "textModules": "",
                "download": False,
                "storeToDms": doc_config.store_to_dms
            }

            endpoint = "alphaflow-outgoinginvoice/outgoinginvoiceservice/outgoinginvoices/word"

            # Add Accept-Language header for German document generation
            headers = {"Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"}

            response = self.dvelop_client.post(
                endpoint=endpoint,
                payload=payload,
                headers=headers
            )

            if response:
                self.logger.info(f"✅ Dokumentgenerierung erfolgreich für Rechnung {invoice_id}")
                document_id = response.get('id') if isinstance(response, dict) else None
                return DocumentGenerationResult(
                    success=True,
                    document_id=document_id
                )
            else:
                error_msg = "API returned no response"
                self.logger.warning(f"⚠ Dokumentgenerierung fehlgeschlagen: {error_msg}")
                return DocumentGenerationResult(
                    success=False,
                    error_message=error_msg
                )

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Fehler bei Dokumentgenerierung für Rechnung {invoice_id}: {error_msg}")
            return DocumentGenerationResult(
                success=False,
                error_message=error_msg
            )

    def upload_attachment(
        self,
        invoice_id: str,
        pdf_content: bytes,
        filename: str,
        category_id: str
    ) -> DocumentGenerationResult:
        """
        Uploads a PDF attachment to an invoice.

        Args:
            invoice_id: ID of the invoice
            pdf_content: PDF file content as bytes
            filename: Name of the file
            category_id: Category ID for the attachment

        Returns:
            DocumentGenerationResult with success status
        """
        try:
            self.logger.info(f"Lade Anhang '{filename}' für Rechnung {invoice_id} hoch")
            self.logger.debug(f"PDF size: {len(pdf_content)} bytes, Category ID: {category_id}")

            # Prepare multipart form data
            files = {
                'upload': (filename, pdf_content, 'application/pdf')
            }

            data = {
                'upload_fullpath': filename,
                'category': category_id
            }

            # Build endpoint URL
            endpoint = f"{self.endpoint}/{invoice_id}/uploadfile"

            self.logger.debug(f"Upload endpoint: {endpoint}")
            self.logger.debug(f"Form data: upload_fullpath={filename}, category={category_id}")

            # Use the dvelop_client's multipart post method
            response = self.dvelop_client.post_multipart(
                endpoint=endpoint,
                files=files,
                data=data
            )

            if response:
                self.logger.info(f"✅ Anhang erfolgreich hochgeladen für Rechnung {invoice_id}")

                # Try to extract document ID from response
                try:
                    response_data = response.json()
                    attachment_doc_id = response_data.get('id')
                    self.logger.debug(f"Attachment document ID: {attachment_doc_id}")
                except Exception:
                    attachment_doc_id = None

                return DocumentGenerationResult(
                    success=True,
                    document_id=attachment_doc_id or invoice_id
                )
            else:
                error_msg = "Upload fehlgeschlagen - Server returned error"
                self.logger.error(f"❌ {error_msg}")
                return DocumentGenerationResult(
                    success=False,
                    error_message=error_msg
                )

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Fehler beim Hochladen des Anhangs: {error_msg}")
            return DocumentGenerationResult(
                success=False,
                error_message=error_msg
            )

    def start_workflow(self, invoice_id: str, workflow_name: str) -> bool:
        """
        Startet den Bearbeitungsworkflow für eine Ausgangsrechnung.

        Args:
            invoice_id: _id der erstellten Ausgangsrechnung
            workflow_name: Name des zu startenden Workflows (z.B. "alphaflow_Ausgangsrechnung")

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            endpoint = (
                f"alphaflow-outgoinginvoice/workflowservice/"
                f"workflowinstance_outgoinginvoice/workflow/start/{workflow_name}"
            )
            params = {'reference': invoice_id}

            self.logger.info(f"Starte Workflow '{workflow_name}' für Rechnung {invoice_id}")

            response = self.dvelop_client.service_client.execute_authenticated_request(
                method='GET',
                endpoint=endpoint,
                parameters=params
            )

            if response and response.status_code in [200, 201, 202, 204]:
                self.logger.info(f"✅ Workflow '{workflow_name}' erfolgreich gestartet")
                return True
            else:
                status = response.status_code if response else 'keine Antwort'
                self.logger.error(f"❌ Workflow-Start fehlgeschlagen: HTTP {status}")
                if response:
                    self.logger.debug(f"Response body: {response.text[:200]}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Fehler beim Starten des Workflows '{workflow_name}': {str(e)}")
            return False

    def forward_workflow(self, invoice_id: str, flow_id: str) -> bool:
        """
        Leitet den Workflow einer Ausgangsrechnung über einen bestimmten Kontrollfluss weiter.

        Ruft dazu zunächst die Rechnung ab, um die Workflow-Instanz-ID aus dem
        Attribut 'workflow' zu ermitteln, und sendet dann den Forward-Request.

        Args:
            invoice_id: _id der erstellten Ausgangsrechnung
            flow_id: ID des Kontrollflusses im Workflow (z.B. "Flow_0tuv578")

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Rechnung abrufen, um Workflow-Instanz-ID zu ermitteln
            invoice = self.get_invoice(invoice_id)
            if not invoice:
                self.logger.error(f"❌ Rechnung {invoice_id} konnte nicht abgerufen werden")
                return False

            workflow_instance_id = invoice.get('workflow')
            if not workflow_instance_id:
                self.logger.error(
                    f"❌ Kein Workflow-Instanz-Attribut in Rechnung {invoice_id} gefunden"
                )
                return False

            endpoint = (
                f"alphaflow-outgoinginvoice/workflowservice/"
                f"workflowinstance_outgoinginvoice/workflow/forward/"
                f"{workflow_instance_id}/{flow_id}"
            )

            self.logger.info(
                f"Leite Workflow {workflow_instance_id} über Flow '{flow_id}' weiter"
            )

            response = self.dvelop_client.service_client.execute_authenticated_request(
                method='GET',
                endpoint=endpoint
            )

            if response and response.status_code in [200, 201, 202, 204]:
                self.logger.info(f"✅ Workflow-Weiterleitung erfolgreich")
                return True
            else:
                status = response.status_code if response else 'keine Antwort'
                self.logger.error(f"❌ Workflow-Weiterleitung fehlgeschlagen: HTTP {status}")
                if response:
                    self.logger.debug(f"Response body: {response.text[:200]}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Fehler bei Workflow-Weiterleitung: {str(e)}")
            return False

    def join_documents(
        self,
        invoice_id: str,
        invoice_number: str,
        document_ids: List[str],
        document_type: str
    ) -> DocumentGenerationResult:
        """
        Joins multiple documents into a single PDF.

        Args:
            invoice_id: ID of the invoice
            invoice_number: Invoice number for filename (e.g., "R003100")
            document_ids: List of document IDs to join (invoice document first, then attachments)
            document_type: Document type ID for the joined document

        Returns:
            DocumentGenerationResult with success status
        """
        try:
            self.logger.info(f"Füge {len(document_ids)} Dokumente zusammen für Rechnung {invoice_id}")

            # Create filename: Rechnung_RECHNUNGSNUMMER
            filename = f"Rechnung_{invoice_number}"

            # Join document IDs with comma
            documents_str = ",".join(document_ids)

            payload = {
                "id": invoice_id,
                "documentType": document_type,
                "fileName": filename,
                "documents": documents_str,
                "download": False,
                "storeToDms": True
            }

            endpoint = "alphaflow-outgoinginvoice/outgoinginvoiceservice/outgoinginvoices/documents/join"

            self.logger.debug(f"Join payload: {payload}")

            response = self.dvelop_client.post(
                endpoint=endpoint,
                payload=payload
            )

            if response:
                self.logger.info(f"✅ Dokumente erfolgreich zusammengeführt: {filename}")
                return DocumentGenerationResult(
                    success=True,
                    document_id=invoice_id
                )
            else:
                error_msg = "Dokumenten-Join fehlgeschlagen"
                self.logger.error(f"❌ {error_msg}")
                return DocumentGenerationResult(
                    success=False,
                    error_message=error_msg
                )

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Fehler beim Zusammenführen der Dokumente: {error_msg}")
            return DocumentGenerationResult(
                success=False,
                error_message=error_msg
            )