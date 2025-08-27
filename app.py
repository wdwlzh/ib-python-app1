from datetime import datetime
import os
from flask import Flask, render_template, jsonify, redirect, url_for, request
from database import (
    init_database, add_watchlist_symbol, remove_watchlist_symbols, 
    get_watchlist_with_prices, get_cached_account_info, get_cached_portfolio_data,
    COMPANY_NAMES
)

app = Flask(__name__)

# Initialize database
init_database()

def get_company_name(symbol):
    """Get company name for a symbol"""
    return COMPANY_NAMES.get(symbol.upper(), symbol.upper())

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
        # Try to get cached account info - for now, use first available account
        # In a real app, you might want to let users select which account to view
        account_data, updated_at = get_cached_account_info('ALL')  # placeholder for now
        
        if account_data:
            managed_accounts = account_data.get('managedAccounts', [])
            account_values = account_data.get('accountValues', {})
            return render_template('account_info.html', 
                                 managed_accounts=managed_accounts,
                                 account_values=account_values,
                                 updated_at=updated_at)
        else:
            return render_template('error.html', 
                                 error="No cached account data available. Please ensure the data server is running."), 503
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@app.route('/portfolio')
def portfolio_page():
    try:
        portfolio_data, updated_at = get_cached_portfolio_data()
        
        if portfolio_data:
            return render_template('portfolio.html', 
                                 positions=portfolio_data,
                                 updated_at=updated_at)
        else:
            return render_template('error.html', 
                                 error="No cached portfolio data available. Please ensure the data server is running."), 503
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@app.route('/watchlist')
def watchlist_page():
    try:
        watchlist_data = get_watchlist_with_prices()
        return render_template('watchlist.html', watchlist=watchlist_data)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@app.route('/api/watchlist/add', methods=['POST'])
def api_add_symbol():
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        
        if not symbol:
            return jsonify({'success': False, 'message': 'Symbol is required'}), 400
        
        # Get company name
        company_name = get_company_name(symbol)
        
        success, message = add_watchlist_symbol(symbol, company_name)
        return jsonify({'success': success, 'message': message})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/watchlist/remove', methods=['POST'])
def api_remove_symbols():
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'success': False, 'message': 'No symbols provided'}), 400
        
        success, message = remove_watchlist_symbols(symbols)
        return jsonify({'success': success, 'message': message})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    # Run with threading enabled since we're not using IB connection directly
    app.run(host='0.0.0.0', port=port, threaded=True, debug=True)