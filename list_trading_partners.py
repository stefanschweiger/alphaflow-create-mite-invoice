#!/usr/bin/env python3
"""
List all Trading Partners from Alphaflow
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import yaml

from alphaflow_integration import AlphaflowDvelopClient, TradingPartnerClient

# Load environment
load_dotenv()

# Load config
config_path = Path("config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

try:
    # Create and authenticate client
    dvelop_client = AlphaflowDvelopClient(
        base_url=config['alphaflow']['dvelop_base_url'],
        api_key=config['alphaflow']['dvelop_api_key']
    )

    print("\nAuthenticating with Alphaflow...")
    dvelop_client.authenticate()
    print("✓ Authentication successful\n")

    # Create Trading Partner client
    tp_client = TradingPartnerClient(
        dvelop_client=dvelop_client,
        organization_id=config['alphaflow']['organization_id']
    )

    print("Fetching trading partners...\n")
    trading_partners = tp_client.list_trading_partners()

    if not trading_partners:
        print("No trading partners found.")
        sys.exit(0)

    print(f"{'='*100}")
    print(f"Trading Partners ({len(trading_partners)} total)")
    print(f"{'='*100}\n")

    # Sort by number
    trading_partners_sorted = sorted(
        trading_partners,
        key=lambda tp: int(tp.number) if tp.number and tp.number.isdigit() else 999999
    )

    for tp in trading_partners_sorted[:20]:  # Show first 20
        number = str(tp.number) if tp.number else "N/A"
        name = str(tp.name or tp.company_name or "N/A")
        tp_type = str(tp.type) if tp.type else "N/A"
        tp_id = str(tp.id) if tp.id else "N/A"

        print(f"Number: {number:<10} | ID: {tp_id:<30} | Type: {tp_type:<10} | Name: {name}")

    if len(trading_partners) > 20:
        print(f"\n... and {len(trading_partners) - 20} more\n")

    print(f"\n{'='*100}\n")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
