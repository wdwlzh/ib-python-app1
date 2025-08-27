#!/usr/bin/env python3
"""
Test script to add some symbols to the watchlist
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_database, add_watchlist_symbol, get_watchlist, COMPANY_NAMES

def test_watchlist():
    """Test watchlist functionality"""
    print("Initializing database...")
    init_database()
    
    # Test symbols
    test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'QQQ']
    
    print("Adding test symbols to watchlist...")
    for symbol in test_symbols:
        company_name = COMPANY_NAMES.get(symbol, symbol)
        success, message = add_watchlist_symbol(symbol, company_name)
        print(f"Adding {symbol} ({company_name}): {message}")
    
    print("\nCurrent watchlist:")
    watchlist = get_watchlist()
    for symbol, name in watchlist:
        print(f"  {symbol}: {name}")
    
    print(f"\nTotal symbols in watchlist: {len(watchlist)}")

if __name__ == '__main__':
    test_watchlist()
