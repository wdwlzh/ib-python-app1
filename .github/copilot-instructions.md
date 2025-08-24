# AI Development Guide for Interactive Brokers Python Project

## Project Overview
This project is a Python-based trading application that integrates with Interactive Brokers (IB) TWS platform. It combines a Flask web service for health monitoring with IB position tracking capabilities.

## Key Components

### 1. Flask Web Service (`app.py`)
- Health check endpoint at `/health`
- Environment-aware configuration using `FLASK_ENV`
- Default port 8000 (configurable via `PORT` env var)

### 2. IB Position Tracker (`ib_positions.py`)
- Connects to TWS (Trader Workstation) API
- Retrieves current trading positions
- Uses `ib_insync` library for IB API integration
- Configurable port (7498) for TWS connection

## Development Environment

### Dev Container Configuration
The project uses VS Code Dev Containers with two key files:
- `.devcontainer/devcontainer.json`: VS Code configuration, extensions, port forwarding
- `.devcontainer/Dockerfile`: Python environment setup

### Dependencies
```
flask==3.0.0
ib_insync==0.9.86
pandas==2.1.0
```

## Development Workflow

### Local Development
1. Start TWS/IB Gateway and enable API connections (port 7498)
2. Open in VS Code Dev Container
3. Run Flask app: `python app.py`
4. Check positions: `python ib_positions.py`

### Key Port Numbers
- 8000: Flask web service
- 7498: TWS API connection

### Testing
- Health check: `curl http://localhost:8000/health`
- IB connection: Run `python ib_positions.py` and verify TWS connectivity

## Common Issues & Solutions
1. TWS Connection Issues:
   - Verify TWS is running and API enabled
   - Check port number (7498) in TWS settings
   - Ensure host.docker.internal resolution

2. Flask Port Conflicts:
   - Change port via PORT environment variable
   - Check port forwarding in devcontainer.json

## Best Practices
1. Always use environment variables for configuration
2. Log TWS connection status and errors
3. Handle IB API disconnections gracefully

## Integration Points
- TWS API via `ib_insync`
- Flask HTTP endpoints
- Environment variables for configuration
