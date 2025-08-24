from datetime import datetime
import os
from flask import Flask, render_template, jsonify
from ib_insync import IB
from ib_positions import get_positions
import atexit

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
def index():
    try:
        df = get_positions(ib=ib)
        positions = df.to_dict('records') if not df.empty else []
        return render_template('positions.html', positions=positions)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    # Leave threaded=True; IB connection was created in main thread so event-loop issues are avoided.
    app.run(host='0.0.0.0', port=port, threaded=True)