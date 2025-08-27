import sqlite3
import json
from datetime import datetime
import os

DATABASE_FILE = 'trading_app.db'

# Company name mappings
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

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Watchlist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Price data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            last_price REAL,
            change_pct REAL,
            volume INTEGER,
            bid REAL,
            ask REAL,
            close_price REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (symbol) REFERENCES watchlist (symbol)
        )
    ''')
    
    # Account info cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            data TEXT,  -- JSON data
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Portfolio cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,  -- JSON data
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_watchlist_symbol(symbol, name):
    """Add a symbol to the watchlist"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO watchlist (symbol, name) VALUES (?, ?)', (symbol.upper(), name))
        conn.commit()
        return True, "Symbol added successfully"
    except sqlite3.IntegrityError:
        return False, "Symbol already exists in watchlist"
    except Exception as e:
        return False, f"Error adding symbol: {e}"
    finally:
        conn.close()

def remove_watchlist_symbols(symbols):
    """Remove symbols from the watchlist"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        placeholders = ','.join(['?' for _ in symbols])
        cursor.execute(f'DELETE FROM watchlist WHERE symbol IN ({placeholders})', [s.upper() for s in symbols])
        removed_count = cursor.rowcount
        
        # Also remove price data for these symbols
        cursor.execute(f'DELETE FROM price_data WHERE symbol IN ({placeholders})', [s.upper() for s in symbols])
        
        conn.commit()
        return True, f"Removed {removed_count} symbols"
    except Exception as e:
        return False, f"Error removing symbols: {e}"
    finally:
        conn.close()

def get_watchlist():
    """Get all watchlist symbols"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT symbol, name FROM watchlist ORDER BY symbol')
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting watchlist: {e}")
        return []
    finally:
        conn.close()

def update_price_data(symbol, last_price=None, change_pct=None, volume=None, bid=None, ask=None, close_price=None):
    """Update price data for a symbol"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # First, delete existing price data for this symbol
        cursor.execute('DELETE FROM price_data WHERE symbol = ?', (symbol.upper(),))
        
        # Insert new price data
        cursor.execute('''
            INSERT INTO price_data (symbol, last_price, change_pct, volume, bid, ask, close_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (symbol.upper(), last_price, change_pct, volume, bid, ask, close_price))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating price data for {symbol}: {e}")
        return False
    finally:
        conn.close()

def get_watchlist_with_prices():
    """Get watchlist with latest price data"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT w.symbol, w.name, 
                   COALESCE(p.last_price, 0) as last_price,
                   COALESCE(p.change_pct, 0) as change_pct,
                   COALESCE(p.volume, 0) as volume,
                   p.updated_at
            FROM watchlist w
            LEFT JOIN price_data p ON w.symbol = p.symbol
            ORDER BY w.symbol
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row[0],
                'name': row[1],
                'last_price': round(float(row[2]) if row[2] else 0, 2),
                'change_pct': round(float(row[3]) if row[3] else 0, 2),
                'volume': int(row[4]) if row[4] else 0,
                'updated_at': row[5]
            })
        
        return results
    except Exception as e:
        print(f"Error getting watchlist with prices: {e}")
        return []
    finally:
        conn.close()

def cache_account_info(account_id, data):
    """Cache account information"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # Delete existing cache for this account
        cursor.execute('DELETE FROM account_cache WHERE account_id = ?', (account_id,))
        
        # Insert new cache
        cursor.execute('INSERT INTO account_cache (account_id, data) VALUES (?, ?)', 
                      (account_id, json.dumps(data)))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error caching account info: {e}")
        return False
    finally:
        conn.close()

def get_cached_account_info(account_id):
    """Get cached account information"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT data, updated_at FROM account_cache WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1', 
                      (account_id,))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row[0]), row[1]
        return None, None
    except Exception as e:
        print(f"Error getting cached account info: {e}")
        return None, None
    finally:
        conn.close()

def cache_portfolio_data(data):
    """Cache portfolio data"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # Keep only the latest 10 portfolio snapshots
        cursor.execute('DELETE FROM portfolio_cache WHERE id NOT IN (SELECT id FROM portfolio_cache ORDER BY updated_at DESC LIMIT 9)')
        
        # Insert new cache
        cursor.execute('INSERT INTO portfolio_cache (data) VALUES (?)', (json.dumps(data),))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error caching portfolio data: {e}")
        return False
    finally:
        conn.close()

def get_cached_portfolio_data():
    """Get cached portfolio data"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT data, updated_at FROM portfolio_cache ORDER BY updated_at DESC LIMIT 1')
        row = cursor.fetchone()
        
        if row:
            return json.loads(row[0]), row[1]
        return None, None
    except Exception as e:
        print(f"Error getting cached portfolio data: {e}")
        return None, None
    finally:
        conn.close()

# Initialize database on import
if __name__ == '__main__':
    init_database()
    print("Database initialized successfully")
