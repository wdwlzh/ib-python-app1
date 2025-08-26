from ib_insync import *
import pandas as pd
import numpy as np

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

    # (Removed DailyPnL/UnrealizedPnL-related logic)
        for position in positions:
            acct = position.account
            contract = getattr(position, 'contract', None)
            conId = getattr(contract, 'conId', None) if contract is not None else None

            # derive contract-level metadata when available
            sec_type = getattr(contract, 'secType', None) if contract is not None else None
            # Normalize contract category
            if sec_type is not None and str(sec_type).upper().startswith('OPT'):
                contract_type = 'Option'
            elif sec_type is not None and str(sec_type).upper().startswith('FUT'):
                contract_type = 'Future'
            else:
                contract_type = sec_type

            # Common option/future fields
            last_date = None
            strike = None
            option_type = None
            if contract is not None:
                last_date = getattr(contract, 'lastTradeDateOrContractMonth', None) or getattr(contract, 'lastTradeDate', None)
                # strike and right/option type for options
                strike = getattr(contract, 'strike', None)
                right = getattr(contract, 'right', None)
                if right is not None:
                    r = str(right).upper()
                    if r in ('C', 'CALL'):
                        option_type = 'Call'
                    elif r in ('P', 'PUT'):
                        option_type = 'Put'

            data = {
                    'Account': acct,
                    'Contract': contract_type,
                    'Symbol': getattr(contract, 'symbol', None) if contract is not None else None,
                    'LastDate': last_date,
                    'OptionType': option_type,
                    'StrikePrice': strike,
                    'SecType': sec_type,
                    'Exchange': getattr(contract, 'exchange', None) if contract is not None else None,
                    'Currency': getattr(contract, 'currency', None) if contract is not None else None,
                    'Position': position.position,
                    'AvgCost': position.avgCost,
                    # DailyPnL and UnrealizedPnL removed per request
                }
            position_data.append(data)

        df = pd.DataFrame(position_data)

        # normalize numeric columns
        df['StrikePrice'] = pd.to_numeric(df.get('StrikePrice'), errors='coerce')
        df['AvgCost'] = pd.to_numeric(df.get('AvgCost'), errors='coerce')
        df['Position'] = pd.to_numeric(df.get('Position'), errors='coerce').fillna(0)

        # Grouping as requested by Account, Contract, Symbol, Last Date, Option Type, Strike Price
        group_cols = ['Account', 'Contract', 'Symbol', 'LastDate', 'OptionType', 'StrikePrice']

        def agg_group(g):
            total_pos = g['Position'].sum()
            # weighted avg cost by absolute position size when possible
            try:
                weights = g['Position'].abs()
                if weights.sum() > 0:
                    avg_cost = np.average(g['AvgCost'].fillna(0).astype(float), weights=weights)
                else:
                    avg_cost = pd.to_numeric(g['AvgCost'], errors='coerce').mean()
            except Exception:
                avg_cost = pd.to_numeric(g['AvgCost'], errors='coerce').mean()

            currency = g['Currency'].iloc[0] if not g['Currency'].empty else None

            return pd.Series({
                'Position': total_pos,
                'Currency': currency,
                'AvgCost': avg_cost
            })

        grouped = df.groupby(group_cols, dropna=False).apply(agg_group).reset_index()

        # Sort: OptionType ascending (Call before Put), StrikePrice descending
        sort_cols = ['Account', 'Contract', 'Symbol', 'LastDate', 'OptionType', 'StrikePrice']
        ascending = [True, True, True, True, True, False]
        try:
            grouped = grouped.sort_values(by=sort_cols, ascending=ascending, na_position='last')
        except Exception:
            # fallback to simple sort if any column missing
            grouped = grouped

        return grouped

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