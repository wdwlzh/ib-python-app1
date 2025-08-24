from datetime import datetime
import os
from flask import Flask, render_template, jsonify, redirect, url_for
from ib_insync import IB
from ib_positions import get_positions
import atexit
from ib_positions import get_account_info

app = Flask(__name__)

# Create and reuse a single IB connection (run in main thread before Flask spawns worker threads)
ib = IB()
try:
    ib.connect('host.docker.internal', 7498, clientId=1)
    print("Connected to IB at host.docker.internal:7498")
except Exception as e:
    print(f"Warning: could not connect to IB at startup: {e}")

# Ensure we disconnect on container/app exit
def _disconnect_ib():
    try:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected from IB")
    except Exception:
        pass

atexit.register(_disconnect_ib)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })
@app.route('/')
def root():
    # Redirect root to the dashboard page
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/account')
def account_page():
    try:
        acct_info = get_account_info(ib=ib)
        managed_accounts = acct_info.get('managedAccounts', [])
        account_values = acct_info.get('accountValues', {})
        return render_template('account_info.html', managed_accounts=managed_accounts,
                               account_values=account_values)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@app.route('/portfolio')
def portfolio_page():
    try:
        df = get_positions(ib=ib)
        positions = df.to_dict('records') if not df.empty else []
        # Render a portfolio page (separate template) with a Back button
        return render_template('portfolio.html', positions=positions)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    # Leave threaded=True; IB connection was created in main thread so event-loop issues are avoided.
    app.run(host='0.0.0.0', port=port, threaded=True)