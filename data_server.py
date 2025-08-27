#!/usr/bin/env python3
"""
Data Server - Maintains persistent TWS connection and updates database
"""

import time
import signal
import sys
from datetime import datetime, timedelta
import threading
from ib_insync import IB, Stock
from database import (
    init_database, get_watchlist, update_price_data, 
    cache_account_info, cache_portfolio_data
)
from ib_positions import get_positions, get_account_info

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
}

class DataServer:
    def __init__(self):
        self.ib = None
        self.running = False
        self.watchlist_update_interval = 5  # seconds
        self.portfolio_update_interval = 30  # seconds
        self.account_update_interval = 60  # seconds
        
        # Timestamps for different update cycles
        self.last_watchlist_update = datetime.min
        self.last_portfolio_update = datetime.min
        self.last_account_update = datetime.min
        
    def connect_to_ib(self):
        """Connect to Interactive Brokers TWS"""
        try:
            self.ib = IB()
            self.ib.connect('host.docker.internal', 7498, clientId=10)
            print(f"[{datetime.now()}] Connected to IB TWS")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] Error connecting to IB: {e}")
            return False
    
    def disconnect_from_ib(self):
        """Disconnect from Interactive Brokers TWS"""
        if self.ib and self.ib.isConnected():
            try:
                self.ib.disconnect()
                print(f"[{datetime.now()}] Disconnected from IB TWS")
            except Exception as e:
                print(f"[{datetime.now()}] Error disconnecting from IB: {e}")
    
    def update_watchlist_prices(self):
        """Update prices for all watchlist symbols"""
        if not self.ib or not self.ib.isConnected():
            print(f"[{datetime.now()}] IB not connected, skipping watchlist update")
            return
        
        try:
            watchlist = get_watchlist()
            if not watchlist:
                return
            
            print(f"[{datetime.now()}] Updating prices for {len(watchlist)} symbols")
            
            for symbol, name in watchlist:
                try:
                    # Create stock contract
                    stock = Stock(symbol, 'SMART', 'USD')
                    qualified = self.ib.qualifyContracts(stock)
                    
                    if not qualified:
                        print(f"Could not qualify contract for {symbol}")
                        continue
                    
                    # Request market data with delayed data allowed
                    ticker = self.ib.reqMktData(qualified[0], '', True, False)
                    time.sleep(2)  # Wait longer for data
                    
                    # If no data, try requesting delayed market data explicitly
                    if not ticker or (not ticker.last and not ticker.close and not ticker.bid and not ticker.ask):
                        # Request delayed market data (usually free)
                        self.ib.reqMarketDataType(3)  # 3 = delayed market data
                        ticker = self.ib.reqMktData(qualified[0], '', True, False)
                        time.sleep(2)  # Wait for delayed data
                    
                    # Extract price information
                    last_price = 0
                    change_pct = 0
                    volume = 0
                    bid = 0
                    ask = 0
                    close_price = 0
                    
                    if ticker:
                        # Get last price - try multiple sources
                        if ticker.last and ticker.last > 0:
                            last_price = float(ticker.last)
                        elif hasattr(ticker, 'marketPrice') and ticker.marketPrice() and ticker.marketPrice() > 0:
                            last_price = float(ticker.marketPrice())
                        elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                            bid = float(ticker.bid)
                            ask = float(ticker.ask)
                            last_price = (bid + ask) / 2
                        elif ticker.close and ticker.close > 0:
                            last_price = float(ticker.close)
                        
                        # Get bid/ask separately if available
                        if ticker.bid and ticker.bid > 0 and bid == 0:
                            bid = float(ticker.bid)
                        if ticker.ask and ticker.ask > 0 and ask == 0:
                            ask = float(ticker.ask)
                            
                        # Get close price
                        if ticker.close and ticker.close > 0:
                            close_price = float(ticker.close)
                            
                        # Get volume
                        if ticker.volume and ticker.volume > 0:
                            volume = int(ticker.volume)
                        
                        # Calculate change percentage
                        if close_price > 0 and last_price > 0:
                            change_pct = ((last_price - close_price) / close_price) * 100
                        
                        print(f"Raw data for {symbol}: last={ticker.last}, bid={ticker.bid}, ask={ticker.ask}, close={ticker.close}, volume={ticker.volume}")
                    
                    # If we still don't have a price, try to get historical data as fallback
                    if last_price == 0:
                        try:
                            bars = self.ib.reqHistoricalData(
                                qualified[0],
                                endDateTime='',
                                durationStr='1 D',
                                barSizeSetting='1 day',
                                whatToShow='TRADES',
                                useRTH=True,
                                formatDate=1
                            )
                            if bars:
                                last_bar = bars[-1]
                                last_price = float(last_bar.close)
                                if len(bars) > 1:
                                    prev_close = float(bars[-2].close)
                                    if prev_close > 0:
                                        change_pct = ((last_price - prev_close) / prev_close) * 100
                                volume = int(last_bar.volume) if last_bar.volume else 0
                                close_price = last_price
                                print(f"Using historical data for {symbol}: ${last_price:.2f}")
                        except Exception as hist_e:
                            print(f"Historical data failed for {symbol}: {hist_e}")
                    
                    # Update database
                    success = update_price_data(
                        symbol, last_price, change_pct, volume, bid, ask, close_price
                    )
                    
                    if success:
                        print(f"Updated {symbol}: ${last_price:.2f} ({change_pct:+.2f}%)")
                    
                    # Cancel market data subscription
                    self.ib.cancelMktData(qualified[0])
                    
                except Exception as e:
                    print(f"Error updating price for {symbol}: {e}")
                    # Still update database with zero values to show symbol exists
                    update_price_data(symbol, 0, 0, 0, 0, 0, 0)
                    
        except Exception as e:
            print(f"[{datetime.now()}] Error in update_watchlist_prices: {e}")
    
    def update_portfolio_cache(self):
        """Update portfolio cache"""
        if not self.ib or not self.ib.isConnected():
            print(f"[{datetime.now()}] IB not connected, skipping portfolio update")
            return
        
        try:
            print(f"[{datetime.now()}] Updating portfolio cache")
            df = get_positions(ib=self.ib)
            positions = df.to_dict('records') if not df.empty else []
            cache_portfolio_data(positions)
            print(f"[{datetime.now()}] Portfolio cache updated with {len(positions)} positions")
        except Exception as e:
            print(f"[{datetime.now()}] Error updating portfolio cache: {e}")
    
    def update_account_cache(self):
        """Update account cache"""
        if not self.ib or not self.ib.isConnected():
            print(f"[{datetime.now()}] IB not connected, skipping account update")
            return
        
        try:
            print(f"[{datetime.now()}] Updating account cache")
            account_info = get_account_info(ib=self.ib)
            
            # Cache for each managed account
            for account_id in account_info.get('managedAccounts', []):
                account_data = {
                    'managedAccounts': account_info['managedAccounts'],
                    'accountValues': account_info['accountValues'].get(account_id, {})
                }
                cache_account_info(account_id, account_data)
            
            print(f"[{datetime.now()}] Account cache updated")
        except Exception as e:
            print(f"[{datetime.now()}] Error updating account cache: {e}")
    
    def run_update_cycle(self):
        """Run one complete update cycle"""
        now = datetime.now()
        
        # Update watchlist prices every few seconds
        if (now - self.last_watchlist_update).total_seconds() >= self.watchlist_update_interval:
            self.update_watchlist_prices()
            self.last_watchlist_update = now
        
        # Update portfolio every 30 seconds
        if (now - self.last_portfolio_update).total_seconds() >= self.portfolio_update_interval:
            self.update_portfolio_cache()
            self.last_portfolio_update = now
        
        # Update account info every minute
        if (now - self.last_account_update).total_seconds() >= self.account_update_interval:
            self.update_account_cache()
            self.last_account_update = now
    
    def start(self):
        """Start the data server"""
        print(f"[{datetime.now()}] Starting data server...")
        
        # Initialize database
        init_database()
        
        # Connect to IB
        if not self.connect_to_ib():
            print("Failed to connect to IB. Exiting.")
            return
        
        self.running = True
        print(f"[{datetime.now()}] Data server started successfully")
        
        try:
            while self.running:
                self.run_update_cycle()
                time.sleep(1)  # Sleep for 1 second between cycles
                
        except KeyboardInterrupt:
            print(f"\n[{datetime.now()}] Received interrupt signal")
        except Exception as e:
            print(f"[{datetime.now()}] Unexpected error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the data server"""
        print(f"[{datetime.now()}] Stopping data server...")
        self.running = False
        self.disconnect_from_ib()
        print(f"[{datetime.now()}] Data server stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n[{datetime.now()}] Received signal {signum}")
    server.stop()
    sys.exit(0)

if __name__ == '__main__':
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start server
    server = DataServer()
    server.start()
