import json
import os
from halal_screener import build_halal_universe

# Path to the real halal universe
cache_path = os.path.join(os.path.dirname(__file__), '..', 'halal_universe.json')

# Get full list of tickers from the existing file
tickers = [
    "SOFI", "PLTR", "HOOD", "SNAP", "PINS", "DKNG", "U", "F", "RIVN", "LCID", 
    "NIO", "PLUG", "FCEL", "MARA", "RIOT", "COIN", "CCL", "AAL", "DAL", "NCLH", 
    "DNA", "CRSP", "BEAM", "AMD", "INTC", "CSCO", "T", "UBER"
]

print(f"Found {len(tickers)} tickers in universe. Running ultra-strict screen...")

# Temporarily patch CACHE_FILE in halal_screener so it writes to the correct location
import halal_screener
halal_screener.CACHE_FILE = cache_path

# Run the screen (force refresh to re-evaluate all)
res = build_halal_universe(tickers, force_refresh=True)

halal_count = sum(1 for d in res.values() if d['compliant'])
print(f"Ultra-Strict Screen Complete: {halal_count} / {len(tickers)} are halal.")
