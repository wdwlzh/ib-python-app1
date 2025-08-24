from ib_insync import *
import pandas as pd

def get_positions(ib: IB = None):
    """
    Return positions as a pandas DataFrame.
    If an IB instance is provided, reuse it; otherwise create a temporary connection.
    """
    own_ib = False
    if ib is None:
        ib = IB()
        own_ib = True

    try:
        if not ib.isConnected():
            # synchronous connect (run from main thread when possible)
            ib.connect('host.docker.internal', 7498, clientId=1)

        positions = ib.positions()

        position_data = []
        for position in positions:
            data = {
                'Account': position.account,
                'Symbol': getattr(position.contract, 'symbol', None),
                'SecType': getattr(position.contract, 'secType', None),
                'Exchange': getattr(position.contract, 'exchange', None),
                'Currency': getattr(position.contract, 'currency', None),
                'Position': position.position,
                'AvgCost': position.avgCost
            }
            position_data.append(data)

        df = pd.DataFrame(position_data)
        return df

    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame()

    finally:
        # only disconnect if we created the connection here
        if own_ib:
            try:
                ib.disconnect()
            except Exception:
                pass

if __name__ == '__main__':
    df = get_positions()
    print(df)


def get_account_info(ib: IB = None):
    """
    Return account information as a dict:
      {
        'managedAccounts': [<accountId>, ...],
        'accountValues': { accountId: { tag: {'value': ..., 'currency': ...}, ... }, ... }
      }
    If no IB instance is provided, a temporary connection is created and closed.
    """
    own_ib = False
    if ib is None:
        ib = IB()
        own_ib = True

    try:
        if not ib.isConnected():
            ib.connect('host.docker.internal', 7498, clientId=1)

        managed = ib.managedAccounts()
        account_values = ib.accountValues()

        accounts = {}
        for av in account_values:
            acct = av.account
            accounts.setdefault(acct, {})
            tag = av.tag
            val_raw = av.value
            # try to convert numeric values to float when possible
            try:
                val_num = float(val_raw.replace(',', ''))
            except Exception:
                val_num = val_raw
            accounts[acct][tag] = {'value': val_num, 'currency': av.currency}

        return {'managedAccounts': managed, 'accountValues': accounts}

    except Exception as e:
        print(f"Error fetching account info: {e}")
        return {'managedAccounts': [], 'accountValues': {}}

    finally:
        if own_ib:
            try:
                ib.disconnect()
            except Exception:
                pass