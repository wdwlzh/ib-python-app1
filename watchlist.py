from ib_insync import IB, Stock
import json
import os

# Simple file-based storage for watchlist symbols
WATCHLIST_FILE = 'watchlist.json'

# Company name mappings (you can expand this or use a financial API)
COMPANY_NAMES = {
    'AAPL': 'Apple Inc.',
    'GOOGL': 'Alphabet Inc.',
    'MSFT': 'Microsoft Corp.',
    'AMZN': 'Amazon.com Inc.',
    'TSLA': 'Tesla Inc.',
    'META': 'Meta Platforms Inc.',
    'NVDA': 'NVIDIA Corp.',
    'QQQ': 'Invesco QQQ Trust',
    'SPY': 'SPDR S&P 500 ETF',
    'IWM': 'iShares Russell 2000 ETF',
    'VTI': 'Vanguard Total Stock Market ETF',
    'NFLX': 'Netflix Inc.',
    'AMD': 'Advanced Micro Devices',
    'INTC': 'Intel Corp.',
    'CRM': 'Salesforce Inc.',
    'ORCL': 'Oracle Corp.',
    'IBM': 'International Business Machines',
    'BA': 'Boeing Co.',
    'GE': 'General Electric Co.',
    'JPM': 'JPMorgan Chase & Co.',
    'BAC': 'Bank of America Corp.',
    'WFC': 'Wells Fargo & Co.',
    'C': 'Citigroup Inc.',
    'GS': 'Goldman Sachs Group Inc.',
    'MS': 'Morgan Stanley',
    'V': 'Visa Inc.',
    'MA': 'Mastercard Inc.',
    'PYPL': 'PayPal Holdings Inc.',
    'SQ': 'Block Inc.',
    'XOM': 'Exxon Mobil Corp.',
    'CVX': 'Chevron Corp.',
    'COP': 'ConocoPhillips',
    'PG': 'Procter & Gamble Co.',
    'JNJ': 'Johnson & Johnson',
    'PFE': 'Pfizer Inc.',
    'MRK': 'Merck & Co Inc.',
    'ABT': 'Abbott Laboratories',
    'TMO': 'Thermo Fisher Scientific',
    'UNH': 'UnitedHealth Group Inc.',
    'KO': 'Coca-Cola Co.',
    'PEP': 'PepsiCo Inc.',
    'WMT': 'Walmart Inc.',
    'HD': 'Home Depot Inc.',
    'LOW': 'Lowe\'s Companies Inc.',
    'TGT': 'Target Corp.',
    'DIS': 'Walt Disney Co.'
}

def get_company_name(symbol):
    """Get company name for a symbol"""
    return COMPANY_NAMES.get(symbol.upper(), symbol.upper())

def load_watchlist():
    """Load watchlist symbols from file"""
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r') as f:
                data = json.load(f)
            
            # Migrate old format to new format with company names
            updated = False
            for item in data:
                if 'name' not in item or item['name'] == item['symbol']:
                    item['name'] = get_company_name(item['symbol'])
                    updated = True
            
            # Save updated data if migration occurred
            if updated:
                save_watchlist(data)
            
            return data
        except Exception as e:
            print(f"Error loading watchlist: {e}")
            return []
    return []

def save_watchlist(symbols):
    """Save watchlist symbols to file"""
    try:
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(symbols, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving watchlist: {e}")
        return False

def add_symbol(symbol):
    """Add a symbol to the watchlist"""
    watchlist = load_watchlist()
    symbol_upper = symbol.upper()
    
    # Check if symbol already exists
    for item in watchlist:
        if item['symbol'] == symbol_upper:
            return False, "Symbol already exists in watchlist"
    
    # Add new symbol with company name
    watchlist.append({
        'name': get_company_name(symbol_upper),
        'symbol': symbol_upper
    })
    
    if save_watchlist(watchlist):
        return True, "Symbol added successfully"
    else:
        return False, "Failed to save watchlist"

def remove_symbols(symbols_to_remove):
    """Remove symbols from the watchlist"""
    watchlist = load_watchlist()
    symbols_set = set(s.upper() for s in symbols_to_remove)
    
    # Filter out symbols to remove
    new_watchlist = [item for item in watchlist if item['symbol'] not in symbols_set]
    
    if save_watchlist(new_watchlist):
        return True, f"Removed {len(watchlist) - len(new_watchlist)} symbols"
    else:
        return False, "Failed to save watchlist"

def get_watchlist_with_prices(ib: IB = None):
    """Get watchlist with current prices from IB"""
    watchlist = load_watchlist()
    result = []
    
    # If no IB connection provided or not connected, return watchlist without prices
    if ib is None or not ib.isConnected():
        print("IB not connected, returning watchlist without prices")
        for item in watchlist:
            result.append({
                'name': item.get('name', get_company_name(item['symbol'])),
                'symbol': item['symbol'],
                'last_price': 0,
                'change_pct': 0,
                'volume': 0
            })
        return result
    
    try:
        for item in watchlist:
            symbol = item['symbol']
            try:
                # Create stock contract
                stock = Stock(symbol, 'SMART', 'USD')
                qualified = ib.qualifyContracts(stock)
                
                if not qualified:
                    print(f"Could not qualify contract for {symbol}")
                    result.append({
                        'name': item.get('name', get_company_name(symbol)),
                        'symbol': symbol,
                        'last_price': 0,
                        'change_pct': 0,
                        'volume': 0
                    })
                    continue
                
                # Request market data snapshot (snapshot=True for one-time data)
                ticker = ib.reqMktData(qualified[0], '', True, False)
                
                # Wait for data to arrive
                ib.sleep(3)
                
                # Get price data
                last_price = 0
                change_pct = 0
                volume = 0
                
                if ticker:
                    # Try different price sources
                    if ticker.last and ticker.last > 0:
                        last_price = float(ticker.last)
                    elif ticker.marketPrice() and ticker.marketPrice() > 0:
                        last_price = float(ticker.marketPrice())
                    elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                        last_price = (float(ticker.bid) + float(ticker.ask)) / 2
                    elif ticker.close and ticker.close > 0:
                        last_price = float(ticker.close)
                    
                    # Calculate change percentage
                    if ticker.close and ticker.close > 0 and last_price > 0:
                        close_price = float(ticker.close)
                        change_pct = ((last_price - close_price) / close_price) * 100
                    
                    # Get volume
                    if ticker.volume and ticker.volume > 0:
                        volume = int(ticker.volume)
                    
                    print(f"Got data for {symbol}: price={last_price}, change={change_pct}, volume={volume}")
                
                result.append({
                    'name': item.get('name', get_company_name(symbol)),
                    'symbol': symbol,
                    'last_price': round(last_price, 2),
                    'change_pct': round(change_pct, 2),
                    'volume': volume
                })
                
                # Cancel market data subscription
                ib.cancelMktData(qualified[0])
                
            except Exception as e:
                print(f"Error getting data for {symbol}: {e}")
                result.append({
                    'name': item.get('name', get_company_name(symbol)),
                    'symbol': symbol,
                    'last_price': 0,
                    'change_pct': 0,
                    'volume': 0
                })
        
        return result
        
    except Exception as e:
        print(f"Error in get_watchlist_with_prices: {e}")
        # Return basic data without prices
        for item in watchlist:
            result.append({
                'name': item.get('name', get_company_name(item['symbol'])),
                'symbol': item['symbol'],
                'last_price': 0,
                'change_pct': 0,
                'volume': 0
            })
        return result
