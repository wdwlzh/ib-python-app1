from datetime import datetime
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def hello():
    return jsonify({
        'message': 'Hello from Python Dev Container!',
        'environment': os.getenv('FLASK_ENV', 'development')
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)