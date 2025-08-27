#!/bin/bash
# Startup script for the trading application

# Function to cleanup background processes on exit
cleanup() {
    echo "Shutting down..."
    if [ ! -z "$DATA_SERVER_PID" ]; then
        kill $DATA_SERVER_PID 2>/dev/null
    fi
    if [ ! -z "$WEB_SERVER_PID" ]; then
        kill $WEB_SERVER_PID 2>/dev/null
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "Starting Trading Application..."

# Initialize database
echo "Initializing database..."
python3 database.py

# Start data server in background
echo "Starting data server..."
python3 data_server.py &
DATA_SERVER_PID=$!

# Wait a few seconds for data server to start
sleep 3

# Start web server
echo "Starting web server..."
python3 app.py &
WEB_SERVER_PID=$!

echo "Trading application started successfully!"
echo "Data Server PID: $DATA_SERVER_PID"
echo "Web Server PID: $WEB_SERVER_PID"
echo "Web interface available at: http://localhost:8000"
echo "Press Ctrl+C to stop all servers"

# Wait for either process to exit
wait
