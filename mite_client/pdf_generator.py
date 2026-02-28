"""
PDF Generator for mite time entry reports.
Generates a professional-looking PDF report from time entries.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pathlib import Path
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from .models import TimeEntry


class MiteTimeReportPDFGenerator:
    """Generates PDF reports from mite time entries"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Simple title style
        self.styles.add(ParagraphStyle(
            name='SimpleTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=20,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Simple info text style
        self.styles.add(ParagraphStyle(
            name='SimpleInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            fontName='Helvetica'
        ))

    def generate_report(
        self,
        time_entries: List[TimeEntry],
        customer_name: str,
        project_name: str,
        period_start: date,
        period_end: date,
        output_path: Optional[Path] = None
    ) -> bytes:
        """
        Generate a PDF report from time entries.

        Args:
            time_entries: List of time entries to include
            customer_name: Name of the customer
            project_name: Name of the project
            period_start: Start date of the reporting period
            period_end: End date of the reporting period
            output_path: Optional path to save PDF file

        Returns:
            PDF content as bytes
        """
        # Create PDF in memory
        buffer = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )

        # Build content
        story = []

        # Title
        title = Paragraph("<b>Dienstleistungsnachweis</b>", self.styles['SimpleTitle'])
        story.append(title)
        story.append(Spacer(1, 10))

        # Simple header with project and period info
        header_text = (
            f"<b>{customer_name} - {project_name}</b><br/>"
            f"Zeitraum: {period_start.strftime('%d.%m.%Y')} - {period_end.strftime('%d.%m.%Y')}"
        )
        header = Paragraph(header_text, self.styles['SimpleInfo'])
        story.append(header)
        story.append(Spacer(1, 15))

        # Time entries table
        table = self._create_time_entries_table(time_entries)
        story.append(table)

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Save to file if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)

        return pdf_bytes

    def _create_time_entries_table(self, time_entries: List[TimeEntry]) -> Table:
        """Create table with time entry details"""
        # Sort entries by date
        sorted_entries = sorted(time_entries, key=lambda e: e.date_at)

        # Table header
        data = [
            ['Datum', 'Mitarbeiter', 'Leistung', 'Notiz', 'Stunden']
        ]

        # Add entries
        for entry in sorted_entries:
            # Handle date formatting - date_at can be string or date object
            if isinstance(entry.date_at, str):
                # Parse string date (format: YYYY-MM-DD)
                try:
                    date_obj = datetime.strptime(entry.date_at, '%Y-%m-%d').date()
                    date_str = date_obj.strftime('%d.%m.%Y')
                except ValueError:
                    date_str = entry.date_at
            else:
                date_str = entry.date_at.strftime('%d.%m.%Y')

            # Format hours with comma as decimal separator
            hours_str = f"{entry.hours:.2f}".replace('.', ',')

            # Use Paragraph for note to enable word wrapping
            note_text = entry.note or '-'
            note_para = Paragraph(note_text, self.styles['Normal'])

            data.append([
                date_str,
                entry.user_name or '-',
                entry.service_name or '-',
                note_para,  # Paragraph enables word wrap
                hours_str
            ])

        # Create table with wider columns to use available space
        # A4 width = 210mm, margins = 2*10mm = 20mm, available = 190mm
        # Give most extra space to the Notiz column for better text wrapping
        table = Table(data, colWidths=[26*mm, 37*mm, 32*mm, 73*mm, 22*mm])

        # Clean table style - white background with horizontal lines only
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, 0), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (3, -1), 'LEFT'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),  # Top alignment for wrapped text
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

            # Only horizontal lines between rows
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        return table

    def _create_summary_table(self, time_entries: List[TimeEntry]) -> Table:
        """Create summary table with totals"""
        # Calculate totals
        total_hours = sum(entry.hours for entry in time_entries)
        total_entries = len(time_entries)
        billable_hours = sum(entry.hours for entry in time_entries if entry.billable)
        non_billable_hours = total_hours - billable_hours

        # Get unique users
        users = set(entry.user_name for entry in time_entries if entry.user_name)

        # Create summary data
        data = [
            ['Zusammenfassung', ''],
            ['Gesamtstunden:', f"{total_hours:.2f} h"],
            ['Davon abrechenbar:', f"{billable_hours:.2f} h"],
            ['Davon nicht abrechenbar:', f"{non_billable_hours:.2f} h"],
            ['Anzahl Einträge:', str(total_entries)],
            ['Anzahl Mitarbeiter:', str(len(users))]
        ]

        # Create table
        table = Table(data, colWidths=[80*mm, 40*mm])

        # Style table
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('SPAN', (0, 0), (-1, 0)),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),

            # Highlight total hours
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.whitesmoke),
        ]))

        return table

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + '...'


def generate_mite_time_report_pdf(
    time_entries: List[TimeEntry],
    customer_name: str,
    project_name: str,
    period_start: date,
    period_end: date,
    output_path: Optional[Path] = None
) -> bytes:
    """
    Convenience function to generate a mite time report PDF.

    Args:
        time_entries: List of time entries
        customer_name: Customer name
        project_name: Project name
        period_start: Start date of period
        period_end: End date of period
        output_path: Optional output file path

    Returns:
        PDF content as bytes
    """
    generator = MiteTimeReportPDFGenerator()
    return generator.generate_report(
        time_entries=time_entries,
        customer_name=customer_name,
        project_name=project_name,
        period_start=period_start,
        period_end=period_end,
        output_path=output_path
    )
