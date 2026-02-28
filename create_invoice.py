#!/usr/bin/env python3
"""
Mite to Alphaflow Invoice CLI

CLI-Programm zum Erstellen von Alphaflow-Rechnungen aus mite Zeiteinträgen.
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import date, datetime

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator

# Import der Module
from mite_client import MiteClient, generate_mite_time_report_pdf
from alphaflow_integration import (
    AlphaflowDvelopClient,
    OutgoingInvoiceClient,
    MiteToInvoiceMapper,
    AlphaflowConfig,
    DocumentGenerationConfig,
    TradingPartnerClient
)
from alphaflow_integration.outgoing_invoice_client import DocumentGenerationResult

# Typer App & Rich Console
app = typer.Typer(help="Create Alphaflow invoices from mite time entries")
console = Console()


# ============================================================================
# Pydantic Models für Config-Validierung
# ============================================================================

class MiteConfig(BaseModel):
    """Mite API Konfiguration"""
    account: str = Field(..., min_length=1, description="Mite account name")
    api_key: str = Field(..., min_length=1, description="Mite API key")


class DocumentGenerationConfigModel(BaseModel):
    """Document generation configuration"""
    doc_template: str = Field(default="609bb93bd152c934f2d7a0b3", min_length=1)
    category: str = Field(default="62456b6cfb9b51283472ed35", min_length=1)
    attachment_category: str = Field(default="62456b7ffb9b51283472ed36", min_length=1)
    document_join_type: str = Field(default="62456b6cfb9b51283472ed35", min_length=1)
    type: str = Field(default="PDF")
    store_to_dms: bool = Field(default=True)


class AlphaflowConfigModel(BaseModel):
    """Alphaflow / d.velop Cloud Konfiguration"""
    dvelop_base_url: str = Field(..., min_length=1, description="d.velop base URL")
    dvelop_api_key: str = Field(..., min_length=1, description="d.velop API key")
    organization_id: str = Field(..., min_length=1, description="Organization ID")
    responsible_administrator_id: str = Field(..., min_length=1, description="Administrator ID")

    default_hourly_rate: float = Field(default=190.0, gt=0)
    default_vat_rate: float = Field(default=19.0, ge=0, le=100)
    default_due_days: int = Field(default=30, gt=0)
    default_currency: str = Field(default="EUR")
    default_trading_partner_id: str = Field(..., min_length=1)
    invoice_type_value: Optional[str] = Field(default=None)

    document_generation: Optional[DocumentGenerationConfigModel] = Field(default_factory=DocumentGenerationConfigModel)


class LoggingConfig(BaseModel):
    """Logging Konfiguration"""
    level: str = Field(default="INFO")

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()


class Config(BaseModel):
    """Vollständige Konfiguration"""
    mite: MiteConfig
    alphaflow: AlphaflowConfigModel
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ============================================================================
# Config-Management
# ============================================================================

def substitute_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Substituiert Umgebungsvariablen in Config-Werten.
    Format: ${VAR_NAME} wird durch os.getenv('VAR_NAME') ersetzt.
    """
    def substitute_value(value):
        if isinstance(value, str):
            # Suche nach ${VAR_NAME} Pattern
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)

            for var_name in matches:
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable '{var_name}' not found")
                value = value.replace(f'${{{var_name}}}', env_value)

            return value
        elif isinstance(value, dict):
            return {k: substitute_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [substitute_value(item) for item in value]
        else:
            return value

    return substitute_value(config_dict)


def load_config(config_path: Path) -> Config:
    """
    Lädt und validiert die Konfiguration aus einer YAML-Datei.

    Args:
        config_path: Pfad zur config.yaml Datei

    Returns:
        Validiertes Config-Objekt

    Raises:
        FileNotFoundError: Wenn Config-Datei nicht existiert
        ValidationError: Wenn Config ungültig ist
        ValueError: Wenn Umgebungsvariablen fehlen
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Please copy config_example.yaml to config.yaml and adjust the values."
        )

    # YAML laden
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    # Umgebungsvariablen substituieren
    config_dict = substitute_env_vars(config_dict)

    # Validierung mit Pydantic
    try:
        config = Config(**config_dict)
        return config
    except ValidationError as e:
        error_msg = "Configuration validation failed:\n"
        for error in e.errors():
            field = ' -> '.join(str(x) for x in error['loc'])
            error_msg += f"  - {field}: {error['msg']}\n"
        raise ValueError(error_msg)


def create_alphaflow_config(
    config: Config,
    trading_partner_override: Optional[str]
) -> AlphaflowConfig:
    """
    Erstellt AlphaflowConfig-Objekt aus geladener Config.

    Args:
        config: Geladene und validierte Config
        trading_partner_override: Optionale Override für Trading Partner ID

    Returns:
        AlphaflowConfig-Objekt
    """
    af_config = config.alphaflow

    # Trading Partner bestimmen
    trading_partner_id = trading_partner_override or af_config.default_trading_partner_id

    # Convert Pydantic DocumentGenerationConfigModel to dataclass DocumentGenerationConfig
    doc_gen_config = None
    if af_config.document_generation:
        doc_gen_config = DocumentGenerationConfig(
            doc_template=af_config.document_generation.doc_template,
            category=af_config.document_generation.category,
            attachment_category=af_config.document_generation.attachment_category,
            document_join_type=af_config.document_generation.document_join_type,
            type=af_config.document_generation.type,
            store_to_dms=af_config.document_generation.store_to_dms
        )

    return AlphaflowConfig(
        dvelop_base_url=af_config.dvelop_base_url,
        dvelop_api_key=af_config.dvelop_api_key,
        outgoing_invoice_endpoint='alphaflow-outgoinginvoice/outgoinginvoiceservice/outgoinginvoices',
        organization_id=af_config.organization_id,
        responsible_administrator_id=af_config.responsible_administrator_id,
        default_hourly_rate=af_config.default_hourly_rate,
        default_vat_rate=af_config.default_vat_rate,
        default_due_days=af_config.default_due_days,
        default_currency=af_config.default_currency,
        default_trading_partner_id=trading_partner_id,
        invoice_type_value=af_config.invoice_type_value,
        document_generation=doc_gen_config
    )


def resolve_trading_partner_number_to_id(
    dvelop_client: AlphaflowDvelopClient,
    organization_id: str,
    trading_partner_number: str
) -> Optional[str]:
    """
    Löst eine Trading Partner Number zu einer ID auf.

    Args:
        dvelop_client: Authentifizierter d.velop Client
        organization_id: Alphaflow Organization ID
        trading_partner_number: Trading Partner Number (z.B. "10001")

    Returns:
        Trading Partner ID oder None wenn nicht gefunden

    Raises:
        Exception bei API-Fehlern
    """
    tp_client = TradingPartnerClient(
        dvelop_client=dvelop_client,
        organization_id=organization_id
    )

    trading_partner_id = tp_client.resolve_number_to_id(trading_partner_number)

    if not trading_partner_id:
        raise ValueError(
            f"Trading Partner with number '{trading_partner_number}' not found.\n"
            f"Please check if the number is correct."
        )

    return trading_partner_id


# ============================================================================
# Output-Formatierung
# ============================================================================

def display_project_summary(summary: Dict[str, Any], trading_partner_id: str):
    """Zeigt Projekt-Zusammenfassung in einer Rich-Table an"""
    table = Table(title="Project Summary", box=box.ROUNDED)

    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    # Convert revenue from cents to EUR
    revenue_cents = summary.get('total_revenue', 0)
    revenue_eur = revenue_cents / 100.0

    table.add_row("Project Name", summary.get('project_name', 'N/A'))
    table.add_row("Project ID", str(summary.get('project_id', 'N/A')))
    table.add_row("Customer", summary.get('customer_name', 'N/A'))
    table.add_row("Total Hours", f"{summary.get('total_hours', 0):.2f}h")
    table.add_row("Total Revenue", f"{revenue_eur:.2f} EUR")
    table.add_row("Trading Partner ID", trading_partner_id)

    console.print(table)


def display_time_entries_table(time_entries: List, billable_only: bool):
    """Zeigt eine Übersicht der Zeiteinträge an"""
    table = Table(title=f"Time Entries ({len(time_entries)} entries)", box=box.ROUNDED)

    table.add_column("Date", style="cyan")
    table.add_column("User", style="yellow")
    table.add_column("Service", style="white")
    table.add_column("Hours", justify="right", style="green")
    table.add_column("Billable", justify="center")

    for entry in time_entries[:10]:  # Zeige nur erste 10
        billable_icon = "✓" if entry.billable else "✗"
        billable_style = "green" if entry.billable else "red"

        # Handle date_at as string or datetime
        if entry.date_at:
            if isinstance(entry.date_at, str):
                date_str = entry.date_at[:10]  # Take YYYY-MM-DD part
            else:
                date_str = entry.date_at.strftime("%Y-%m-%d")
        else:
            date_str = "N/A"

        table.add_row(
            date_str,
            entry.user_name or "N/A",
            entry.service_name or "N/A",
            f"{entry.minutes / 60:.2f}",
            f"[{billable_style}]{billable_icon}[/{billable_style}]"
        )

    if len(time_entries) > 10:
        table.add_row("...", "...", "...", "...", "...", style="dim")

    console.print(table)


def lock_time_entries(mite_client: MiteClient, time_entries: List, verbose: bool = False) -> Dict[str, Any]:
    """
    Sperrt Zeiteinträge in mite nach erfolgreicher Rechnungserstellung.

    Args:
        mite_client: Mite Client Instanz
        time_entries: Liste der zu sperrenden Zeiteinträge
        verbose: Verbose Logging aktivieren

    Returns:
        Dictionary mit Zusammenfassung: {
            'total': Gesamtanzahl,
            'locked': Erfolgreich gesperrte Einträge,
            'already_locked': Bereits gesperrte Einträge,
            'failed': Fehlgeschlagene Einträge,
            'errors': Liste von Fehlern
        }
    """
    logger = logging.getLogger(__name__)

    result = {
        'total': len(time_entries),
        'locked': 0,
        'already_locked': 0,
        'failed': 0,
        'errors': []
    }

    for entry in time_entries:
        try:
            # Überspringe bereits gesperrte Einträge
            if entry.locked:
                result['already_locked'] += 1
                if verbose:
                    logger.debug(f"Eintrag {entry.id} ist bereits gesperrt")
                continue

            # Sperre den Eintrag
            # Hinweis: Die mite API gibt bei erfolgreichen Updates eine leere Response zurück
            # Wir müssen daher nur prüfen, ob keine Exception auftritt
            mite_client.time_entries.update(entry.id, locked=True)

            # Wenn wir hier sind, war das Update erfolgreich
            result['locked'] += 1
            if verbose:
                logger.debug(f"Eintrag {entry.id} erfolgreich gesperrt")

        except Exception as e:
            result['failed'] += 1
            error_msg = f"Eintrag {entry.id}: {str(e)}"
            result['errors'].append(error_msg)
            logger.warning(f"Fehler beim Sperren von Eintrag {entry.id}: {e}")

    return result


def display_lock_summary(lock_result: Dict[str, Any]):
    """Zeigt Zusammenfassung der Zeiteintrag-Sperrung an"""
    table = Table(title="Time Entries Locked", box=box.ROUNDED)

    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="white")

    table.add_row("Total entries", str(lock_result['total']))
    table.add_row("Newly locked", f"[green]{lock_result['locked']}[/green]")
    table.add_row("Already locked", f"[yellow]{lock_result['already_locked']}[/yellow]")

    if lock_result['failed'] > 0:
        table.add_row("Failed", f"[red]{lock_result['failed']}[/red]")

    console.print(table)

    # Zeige Fehler-Details falls vorhanden
    if lock_result['errors'] and len(lock_result['errors']) > 0:
        console.print("\n[yellow]Warnings during time entry locking:[/yellow]")
        for error in lock_result['errors'][:5]:  # Zeige maximal 5 Fehler
            console.print(f"  [yellow]⚠[/yellow] {error}")

        if len(lock_result['errors']) > 5:
            console.print(f"  [dim]... and {len(lock_result['errors']) - 5} more[/dim]")


# ============================================================================
# CLI Commands
# ============================================================================

@app.command()
def create(
    project_id: int = typer.Option(..., "--project-id", "-p", help="Mite project ID"),
    from_date: str = typer.Option(..., "--from", "-f", help="Start date (YYYY-MM-DD)"),
    to_date: str = typer.Option(..., "--to", "-t", help="End date (YYYY-MM-DD)"),
    config_path: Path = typer.Option(
        Path("./config.yaml"),
        "--config", "-c",
        help="Path to config.yaml"
    ),
    billable_only: bool = typer.Option(
        True,
        "--billable-only/--no-billable-only",
        help="Only include billable time entries"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show preview without creating invoice"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Verbose output"
    ),
    trading_partner_id: Optional[str] = typer.Option(
        None,
        "--trading-partner-id",
        help="Override trading partner ID"
    ),
    trading_partner_number: Optional[str] = typer.Option(
        None,
        "--trading-partner-number",
        help="Override trading partner by number (will be resolved to ID)"
    )
):
    """
    Create an Alphaflow invoice from mite time entries.

    Example:
        python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31
    """

    # ========================================================================
    # Setup
    # ========================================================================

    # .env laden
    load_dotenv()

    # Logging konfigurieren
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # ====================================================================
        # 1. Konfiguration laden
        # ====================================================================

        console.print("\n[cyan]Loading configuration...[/cyan]")

        try:
            config = load_config(config_path)
            console.print("[green]✓[/green] Configuration loaded successfully")
        except FileNotFoundError as e:
            console.print(f"[red]✗ {e}[/red]")
            raise typer.Exit(code=1)
        except ValueError as e:
            console.print(f"[red]✗ Configuration error:[/red]\n{e}")
            raise typer.Exit(code=1)

        # Validiere Trading Partner Parameter
        if trading_partner_id and trading_partner_number:
            console.print(
                "[red]✗ Error:[/red] Cannot use both --trading-partner-id and "
                "--trading-partner-number at the same time.\n"
                "Please use only one of them."
            )
            raise typer.Exit(code=1)

        # ====================================================================
        # 2. Datums-Validierung
        # ====================================================================

        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError as e:
            console.print(f"[red]✗ Invalid date format:[/red] {e}")
            console.print("Please use YYYY-MM-DD format (e.g., 2024-12-01)")
            raise typer.Exit(code=1)

        if start_date > end_date:
            console.print(f"[red]✗ Invalid date range:[/red] from_date must be <= to_date")
            raise typer.Exit(code=1)

        # ====================================================================
        # 3. Mite-Zeiteinträge holen
        # ====================================================================

        console.print(f"\n[cyan]Fetching time entries from mite...[/cyan]")
        console.print(f"  Project ID: {project_id}")
        console.print(f"  Date range: {start_date} to {end_date}")
        console.print(f"  Billable only: {billable_only}")
        console.print(f"  Filter: Unlocked entries only")

        try:
            mite_client = MiteClient(
                account=config.mite.account,
                api_key=config.mite.api_key
            )

            time_entries = mite_client.time_entries.get_date_range(
                from_date=start_date,
                to_date=end_date,
                project_id=project_id,
                billable=billable_only,
                locked=False  # Nur nicht-gesperrte Einträge abrufen
            )

            console.print(f"[green]✓[/green] Found {len(time_entries)} time entries (unlocked only)")

        except Exception as e:
            console.print(f"[red]✗ Failed to fetch time entries:[/red] {e}")
            if verbose:
                logger.exception("Mite API error:")
            raise typer.Exit(code=1)

        # ====================================================================
        # 4. Validierung: Mindestens ein Zeiteintrag
        # ====================================================================

        if not time_entries:
            console.print("\n[yellow]⚠ No time entries found[/yellow]")
            console.print(f"No {'billable ' if billable_only else ''}unlocked time entries found for project {project_id}")
            console.print(f"in date range {start_date} to {end_date}")
            console.print("\n[dim]Note: Locked entries are excluded. They may have been invoiced already.[/dim]")
            raise typer.Exit(code=0)

        # ====================================================================
        # 5. Projekt-Daten aggregieren
        # ====================================================================

        console.print(f"\n[cyan]Aggregating project data...[/cyan]")

        project_summaries = mite_client.time_entries.get_project_summary(time_entries)

        if not project_summaries:
            console.print("[red]✗ Failed to aggregate project data[/red]")
            raise typer.Exit(code=1)

        # Wir erwarten genau eine Summary (da wir nach Projekt filtern)
        project_summary = project_summaries[0]

        # ====================================================================
        # 6. Trading Partner Number auflösen (falls angegeben)
        # ====================================================================

        # Wenn trading_partner_number angegeben ist, müssen wir sie zur ID auflösen
        # Dafür müssen wir uns zuerst bei Alphaflow authentifizieren
        resolved_trading_partner_id = trading_partner_id

        if trading_partner_number:
            console.print(f"\n[cyan]Resolving trading partner number...[/cyan]")
            console.print(f"  Number: {trading_partner_number}")

            try:
                # Frühe Authentifizierung für Trading Partner Lookup
                dvelop_client_temp = AlphaflowDvelopClient(
                    base_url=config.alphaflow.dvelop_base_url,
                    api_key=config.alphaflow.dvelop_api_key
                )

                dvelop_client_temp.authenticate()

                # Löse Number zu ID auf
                resolved_trading_partner_id = resolve_trading_partner_number_to_id(
                    dvelop_client=dvelop_client_temp,
                    organization_id=config.alphaflow.organization_id,
                    trading_partner_number=trading_partner_number
                )

                console.print(f"[green]✓[/green] Resolved to ID: {resolved_trading_partner_id}")

            except ValueError as e:
                console.print(f"[red]✗ {e}[/red]")
                raise typer.Exit(code=1)
            except Exception as e:
                console.print(f"[red]✗ Failed to resolve trading partner number:[/red] {e}")
                if verbose:
                    logger.exception("Trading partner resolution error:")
                raise typer.Exit(code=1)

        # ====================================================================
        # 7. Alphaflow Config erstellen
        # ====================================================================

        alphaflow_config = create_alphaflow_config(
            config=config,
            trading_partner_override=resolved_trading_partner_id
        )

        # Trading Partner Info
        used_trading_partner = alphaflow_config.default_trading_partner_id
        is_override = resolved_trading_partner_id is not None

        if trading_partner_number:
            console.print(f"[yellow]ℹ[/yellow] Using trading partner from number: {used_trading_partner}")
        elif is_override:
            console.print(f"[yellow]ℹ[/yellow] Using trading partner override: {used_trading_partner}")
        else:
            console.print(f"[green]✓[/green] Using default trading partner: {used_trading_partner}")

        # ====================================================================
        # 8. Anzeige: Projekt-Zusammenfassung
        # ====================================================================

        console.print()
        display_project_summary(project_summary, used_trading_partner)

        if verbose:
            console.print()
            display_time_entries_table(time_entries, billable_only)

        # ====================================================================
        # 9. DRY-RUN: Nur Vorschau
        # ====================================================================

        if dry_run:
            console.print("\n[yellow]DRY-RUN MODE[/yellow] - No invoice will be created")

            # Zeige was erstellt werden würde
            revenue_eur = project_summary.get('total_revenue', 0) / 100.0
            panel_content = (
                f"Project: {project_summary.get('project_name')}\n"
                f"Hours: {project_summary.get('total_hours'):.2f}h\n"
                f"Amount: {revenue_eur:.2f} EUR\n"
                f"Trading Partner: {used_trading_partner}\n"
                f"Service Period: {start_date} to {end_date}\n"
                f"Invoice Date: {date.today()}"
            )

            console.print(Panel(
                panel_content,
                title="[cyan]Invoice Preview[/cyan]",
                border_style="cyan"
            ))

            console.print("\n[green]✓ Dry-run completed successfully[/green]")
            raise typer.Exit(code=0)

        # ====================================================================
        # 10. Alphaflow authentifizieren
        # ====================================================================

        console.print(f"\n[cyan]Authenticating with Alphaflow...[/cyan]")

        try:
            dvelop_client = AlphaflowDvelopClient(
                base_url=alphaflow_config.dvelop_base_url,
                api_key=alphaflow_config.dvelop_api_key
            )

            dvelop_client.authenticate()
            console.print("[green]✓[/green] Authentication successful")

        except Exception as e:
            console.print(f"[red]✗ Authentication failed:[/red] {e}")
            if verbose:
                logger.exception("Alphaflow authentication error:")
            raise typer.Exit(code=1)

        # ====================================================================
        # 11. Rechnung erstellen
        # ====================================================================

        console.print(f"\n[cyan]Creating invoice in Alphaflow...[/cyan]")

        try:
            invoice_client = OutgoingInvoiceClient(
                dvelop_client=dvelop_client,
                endpoint=alphaflow_config.outgoing_invoice_endpoint
            )

            mapper = MiteToInvoiceMapper(alphaflow_config)

            invoices = mapper.map_project_summaries_to_invoices(
                project_summaries=[project_summary],
                service_period_start=start_date,
                service_period_end=end_date,
                invoice_date=date.today()
            )

            if not invoices:
                console.print("[red]✗ Failed to create invoice data[/red]")
                raise typer.Exit(code=1)

            invoice_data = invoices[0]
            result = invoice_client.create_invoice(invoice_data)

            # Erfolgs-Meldung
            console.print("\n[green]✓ Invoice created successfully![/green]")

            # Details anzeigen
            invoice_id = result.get('id', 'N/A')
            invoice_number = result.get('number', 'N/A')

            if verbose:
                logger.debug(f"Invoice result keys: {list(result.keys()) if result else 'None'}")
                logger.debug(f"Invoice number from result: {invoice_number}")

            # Trigger document generation automatically
            if invoice_id != 'N/A':
                console.print(f"\n[cyan]Generating invoice document...[/cyan]")

                doc_result = invoice_client.generate_invoice_document(
                    invoice_id=invoice_id,
                    doc_config=alphaflow_config.document_generation
                )

                invoice_document_id = None
                if doc_result.success:
                    console.print(f"[green]✓ Document generated successfully[/green]")
                    if doc_result.document_id:
                        invoice_document_id = doc_result.document_id
                        console.print(f"  Document ID: {invoice_document_id}")
                else:
                    console.print(f"[yellow]⚠ Document generation failed:[/yellow] {doc_result.error_message}")
                    console.print(f"[yellow]ℹ Invoice was created successfully (ID: {invoice_id})[/yellow]")
                    if verbose:
                        logger.warning(f"Document generation failed for invoice {invoice_id}: {doc_result.error_message}")

                # Upload time report PDF as attachment
                console.print(f"\n[cyan]Generating and uploading time report PDF...[/cyan]")
                try:
                    # Generate PDF from time entries
                    pdf_content = generate_mite_time_report_pdf(
                        time_entries=time_entries,
                        customer_name=project_summary.get('customer_name', 'Unknown'),
                        project_name=project_summary.get('project_name', 'Unknown'),
                        period_start=start_date,
                        period_end=end_date
                    )

                    # Create filename
                    filename = "Dienstleistungsnachweis.pdf"

                    # Upload to Alphaflow
                    upload_result = invoice_client.upload_attachment(
                        invoice_id=invoice_id,
                        pdf_content=pdf_content,
                        filename=filename,
                        category_id=alphaflow_config.document_generation.attachment_category
                    )

                    if upload_result.success:
                        console.print(f"[green]✓ Time report uploaded successfully[/green]")
                        console.print(f"  Filename: {filename}")

                        attachment_document_id = upload_result.document_id
                        if attachment_document_id:
                            console.print(f"  Attachment Document ID: {attachment_document_id}")

                        # Join documents if both invoice document and attachment upload were successful
                        if invoice_document_id and attachment_document_id and invoice_number != 'N/A':
                            console.print(f"\n[cyan]Joining documents...[/cyan]")
                            try:
                                # Join invoice document and attachment: invoice first, then attachment
                                join_result = invoice_client.join_documents(
                                    invoice_id=invoice_id,
                                    invoice_number=invoice_number,
                                    document_ids=[invoice_document_id, attachment_document_id],
                                    document_type=alphaflow_config.document_generation.document_join_type
                                )

                                if join_result.success:
                                    console.print(f"[green]✓ Documents joined successfully[/green]")
                                    console.print(f"  Filename: Rechnung_{invoice_number}")
                                else:
                                    console.print(f"[yellow]⚠ Document join failed:[/yellow] {join_result.error_message}")
                                    if verbose:
                                        logger.warning(f"Document join failed for invoice {invoice_id}: {join_result.error_message}")

                            except Exception as join_error:
                                console.print(f"[yellow]⚠ Failed to join documents:[/yellow] {join_error}")
                                if verbose:
                                    logger.exception("Document join error:")
                    else:
                        console.print(f"[yellow]⚠ Time report upload failed:[/yellow] {upload_result.error_message}")
                        console.print(f"[yellow]ℹ Invoice and document were created successfully[/yellow]")
                        if verbose:
                            logger.warning(f"Time report upload failed for invoice {invoice_id}: {upload_result.error_message}")

                except Exception as upload_error:
                    console.print(f"[yellow]⚠ Failed to upload time report:[/yellow] {upload_error}")
                    console.print(f"[yellow]ℹ Invoice and document were created successfully[/yellow]")
                    if verbose:
                        logger.exception("Time report upload error:")

            revenue_eur = project_summary.get('total_revenue', 0) / 100.0

            success_panel = (
                f"Invoice ID: {invoice_id}\n"
                f"Project: {project_summary.get('project_name')}\n"
                f"Hours: {project_summary.get('total_hours'):.2f}h\n"
                f"Amount: {revenue_eur:.2f} EUR\n"
                f"Trading Partner: {used_trading_partner}"
            )

            console.print(Panel(
                success_panel,
                title="[green]Invoice Details[/green]",
                border_style="green"
            ))

            # ================================================================
            # 12. Zeiteinträge sperren (nach erfolgreicher Rechnungserstellung)
            # ================================================================

            console.print(f"\n[cyan]Locking time entries in mite...[/cyan]")

            lock_result = lock_time_entries(
                mite_client=mite_client,
                time_entries=time_entries,
                verbose=verbose
            )

            # Zeige Zusammenfassung
            console.print()
            display_lock_summary(lock_result)

            # Erfolgs- oder Warnung-Status
            if lock_result['failed'] == 0:
                console.print(f"\n[green]✓ All time entries locked successfully[/green]")
            elif lock_result['locked'] > 0:
                console.print(f"\n[yellow]⚠ Some time entries could not be locked ({lock_result['failed']} failed)[/yellow]")
            else:
                console.print(f"\n[yellow]⚠ No time entries were locked[/yellow]")

        except Exception as e:
            console.print(f"[red]✗ Failed to create invoice:[/red] {e}")
            if verbose:
                logger.exception("Invoice creation error:")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Operation cancelled by user[/yellow]")
        raise typer.Exit(code=130)
    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error:[/red] {e}")
        if verbose:
            logger.exception("Unexpected error:")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information"""
    console.print("Mite to Alphaflow Invoice CLI v1.0.0")


if __name__ == "__main__":
    app()
