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

        # Convert grouped dataframe into a list of dicts and detect option spreads.
        records = grouped.to_dict('records') if not grouped.empty else []

        output = []
        used = set()
        id_counter = 0

        # Helper to create a safe float or None
        def safe_float(x):
            try:
                return float(x)
            except Exception:
                return None

        for idx, r in enumerate(records):
            if idx in used:
                continue

            # Only consider option spreads when OptionType is present
            key = (r.get('Account'), r.get('Contract'), r.get('Symbol'), r.get('LastDate'), r.get('OptionType'))

            # Search for a matching leg within the same key
            match_idx = None
            for j in range(idx + 1, len(records)):
                s = records[j]
                if (s.get('Account'), s.get('Contract'), s.get('Symbol'), s.get('LastDate'), s.get('OptionType')) != key:
                    continue
                # check absolute position equality and opposite signs
                pos_r = safe_float(r.get('Position')) or 0.0
                pos_s = safe_float(s.get('Position')) or 0.0
                if abs(abs(pos_r) - abs(pos_s)) < 1e-9 and pos_r * pos_s < 0:
                    match_idx = j
                    break

            if match_idx is not None:
                s = records[match_idx]
                used.add(idx)
                used.add(match_idx)
                id_counter += 1
                parent_id = f"row_{id_counter}"

                # children's strike prices
                strike1 = safe_float(r.get('StrikePrice'))
                strike2 = safe_float(s.get('StrikePrice'))
                if strike1 is None or strike2 is None:
                    strike_display = ''
                else:
                    lo, hi = sorted([strike1, strike2])
                    strike_display = f"{lo:.2f}-{hi:.2f}"

                # compute parent AvgCost as total amount of underlying position's size * averagecost
                # (sum of position * avgcost across legs)
                avg1 = safe_float(r.get('AvgCost')) or 0.0
                avg2 = safe_float(s.get('AvgCost')) or 0.0
                pos1 = safe_float(r.get('Position')) or 0.0
                pos2 = safe_float(s.get('Position')) or 0.0
                total_amount = pos1 * avg1 + pos2 * avg2

                # parent position shows the absolute leg size (they are equal)
                parent_position = abs(pos1)

                spread_name = None
                ot = (r.get('OptionType') or '')
                if str(ot).lower().startswith('c'):
                    spread_name = 'Bear Call Spread'
                elif str(ot).lower().startswith('p'):
                    spread_name = 'Bull Put Spread'

                parent = {
                    'id': parent_id,
                    'Account': r.get('Account'),
                    'Contract': r.get('Contract'),
                    'Symbol': r.get('Symbol'),
                    'LastDate': r.get('LastDate'),
                    'OptionType': r.get('OptionType'),
                    'StrikePrice': None,
                    'StrikeDisplay': strike_display,
                    'Position': parent_position,
                    'Currency': r.get('Currency'),
                    'AvgCost': total_amount,
                    'is_spread': True,
                    'spread_name': spread_name
                }

                # child rows (preserve original numeric strike and avgcost)
                child1 = dict(r)
                child1.update({'is_child': True, 'parent_id': parent_id})
                child2 = dict(s)
                child2.update({'is_child': True, 'parent_id': parent_id})

                output.append(parent)
                output.append(child1)
                output.append(child2)
            else:
                # normal single row
                output.append(r)

        # Return a DataFrame so callers that expect a DataFrame continue to work
        out_df = pd.DataFrame(output)

        # Ensure boolean flag columns exist and have proper False for missing values
        if 'is_child' in out_df.columns:
            out_df['is_child'] = out_df['is_child'].fillna(False).astype(bool)
        else:
            out_df['is_child'] = False

        if 'is_spread' in out_df.columns:
            out_df['is_spread'] = out_df['is_spread'].fillna(False).astype(bool)
        else:
            out_df['is_spread'] = False

        return out_df

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