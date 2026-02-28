#!/usr/bin/env python3
"""
List all Trading Partners from Alphaflow
"""

import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
import yaml

from alphaflow_integration import AlphaflowDvelopClient, TradingPartnerClient

parser = argparse.ArgumentParser(description="List Alphaflow Trading Partners")
parser.add_argument("--json", action="store_true", help="Output as JSON array (machine-readable)")
parser.add_argument("--config", default="config-prod.yaml", help="Config file (default: config-prod.yaml)")
args = parser.parse_args()

# Load environment
load_dotenv()

# Load config
config_path = Path(args.config)
with open(config_path) as f:
    config = yaml.safe_load(f)

try:
    dvelop_client = AlphaflowDvelopClient(
        base_url=config['alphaflow']['dvelop_base_url'],
        api_key=config['alphaflow']['dvelop_api_key']
    )

    if not args.json:
        print("\nAuthenticating with Alphaflow...")
    dvelop_client.authenticate()
    if not args.json:
        print("✓ Authentication successful\n")

    tp_client = TradingPartnerClient(
        dvelop_client=dvelop_client,
        organization_id=config['alphaflow']['organization_id']
    )

    if not args.json:
        print("Fetching trading partners...\n")
    trading_partners = tp_client.list_trading_partners()

    if not trading_partners:
        if args.json:
            print("[]")
        else:
            print("No trading partners found.")
        sys.exit(0)

    if args.json:
        output = [
            {
                "number": tp.number,
                "name": tp.name or tp.company_name,
                "id": tp.id,
            }
            for tp in trading_partners
        ]
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(f"{'='*100}")
        print(f"Trading Partners ({len(trading_partners)} total)")
        print(f"{'='*100}\n")

        trading_partners_sorted = sorted(
            trading_partners,
            key=lambda tp: int(tp.number) if tp.number and tp.number.isdigit() else 999999
        )

        for tp in trading_partners_sorted[:20]:
            number = str(tp.number) if tp.number else "N/A"
            name = str(tp.name or tp.company_name or "N/A")
            tp_type = str(tp.type) if tp.type else "N/A"
            tp_id = str(tp.id) if tp.id else "N/A"

            print(f"Number: {number:<10} | ID: {tp_id:<30} | Type: {tp_type:<10} | Name: {name}")

        if len(trading_partners) > 20:
            print(f"\n... and {len(trading_partners) - 20} more\n")

        print(f"\n{'='*100}\n")

except Exception as e:
    if args.json:
        print(json.dumps({"error": str(e)}))
    else:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    sys.exit(1)
