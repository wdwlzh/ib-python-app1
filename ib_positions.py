from ib_insync import *
import pandas as pd

def get_positions():
    # Create IB connection
    ib = IB()
    
    try:
        # Connect to TWS (make sure TWS or IB Gateway is running)
        # Port 7497 for TWS paper trading
        # Port 7496 for TWS live trading
        # Change port to 4001 for IB Gateway live trading
        # Change port to 4002 for IB Gateway paper trading
        ib.connect('host.docker.internal', 7498, clientId=1)
        
        # Get account positions
        positions = ib.positions()
        
        # Convert positions to a more readable format
        position_data = []
        for position in positions:
            data = {
                'Symbol': position.contract.symbol,
                'SecType': position.contract.secType,
                'Exchange': position.contract.exchange,
                'Currency': position.contract.currency,
                'Position': position.position,
                'Avg Cost': position.avgCost
            }
            position_data.append(data)
        
        # Convert to pandas DataFrame for better display
        df = pd.DataFrame(position_data)
        print("\nCurrent Positions:")
        print(df)
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        ib.disconnect()

if __name__ == '__main__':
    get_positions()