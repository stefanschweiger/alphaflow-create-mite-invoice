#!/usr/bin/env python3
"""
Test PDF generation standalone
"""

from datetime import date
from pathlib import Path
from mite_client import MiteClient, generate_mite_time_report_pdf
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config_data = yaml.safe_load(f)

# Create mite client
mite_client = MiteClient(
    account=config_data['mite']['account'],
    api_key=config_data['mite']['api_key']
)

# Get time entries
time_entries = mite_client.time_entries.get_date_range(
    from_date=date(2026, 1, 22),
    to_date=date(2026, 1, 22),
    project_id=4516575,
    billable=True,
    locked=False
)

print(f"Found {len(time_entries)} time entries")

if time_entries:
    # Get project summary for customer/project names
    project_summaries = mite_client.time_entries.get_project_summary(time_entries)
    project_summary = project_summaries[0]

    # Generate PDF
    pdf_content = generate_mite_time_report_pdf(
        time_entries=time_entries,
        customer_name=project_summary.get('customer_name', 'Unknown'),
        project_name=project_summary.get('project_name', 'Unknown'),
        period_start=date(2026, 1, 22),
        period_end=date(2026, 1, 22),
        output_path=Path('test_mite_report.pdf')
    )

    print(f"PDF generated: {len(pdf_content)} bytes")
    print(f"Saved to: test_mite_report.pdf")

    # Try to validate it's a real PDF
    if pdf_content.startswith(b'%PDF'):
        print("✓ Valid PDF header")
    else:
        print("✗ Invalid PDF header")
else:
    print("No time entries found")
