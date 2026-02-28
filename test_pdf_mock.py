#!/usr/bin/env python3
"""
Test PDF generation with mock data
"""

from datetime import date
from pathlib import Path
from mite_client.models import TimeEntry
from mite_client.pdf_generator import generate_mite_time_report_pdf

# Create mock time entries
mock_entries = [
    TimeEntry(
        id=1,
        minutes=90,
        date_at='2026-01-22',
        note='Test entry 1',
        billable=True,
        locked=False,
        user_name='Gorden Kappenberg',
        service_name='Beratung',
        project_name='TESTPROJEKT',
        customer_name='d.velop AG'
    ),
    TimeEntry(
        id=2,
        minutes=120,
        date_at='2026-01-22',
        note='Test entry 2',
        billable=True,
        locked=False,
        user_name='Stefan Schweiger',
        service_name='Beratung',
        project_name='TESTPROJEKT',
        customer_name='d.velop AG'
    )
]

print(f"Generating PDF with {len(mock_entries)} mock entries...")

# Generate PDF
pdf_content = generate_mite_time_report_pdf(
    time_entries=mock_entries,
    customer_name='d.velop AG',
    project_name='TESTPROJEKT',
    period_start=date(2026, 1, 22),
    period_end=date(2026, 1, 22),
    output_path=Path('test_mite_report.pdf')
)

print(f"✓ PDF generated: {len(pdf_content)} bytes")
print(f"✓ Saved to: test_mite_report.pdf")

# Validate PDF header
if pdf_content.startswith(b'%PDF'):
    print("✓ Valid PDF header")
else:
    print("✗ Invalid PDF header")

# Check size
if len(pdf_content) > 1000:
    print(f"✓ Reasonable PDF size: {len(pdf_content)} bytes")
else:
    print(f"⚠ PDF seems too small: {len(pdf_content)} bytes")
