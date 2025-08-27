# Interactive Brokers Trading Application

A modern Python-based trading application that integrates with Interactive Brokers (IB) TWS platform, featuring a Flask web interface and real-time watchlist functionality.

## 🏗️ Architecture

The application uses a **separated architecture** with distinct components:

- **Web Server** (`app.py`) - Flask web interface for viewing data
- **Data Server** (`data_server.py`) - Background service that maintains IB TWS connection and updates database
- **Database** (`database.py`) - SQLite database for storing watchlist symbols and price data
- **Startup Manager** (`start.py`) - Manages both components with proper lifecycle handling

## ✨ Features

### 📊 Dashboard
- **Account Info** - View managed accounts and account summary
- **Portfolio** - Current trading positions with spread detection
- **Watchlist** - Real-time price tracking for selected symbols

### 📈 Watchlist
- **Real-time Prices** - Live price updates from IB TWS (historical data fallback)
- **Company Names** - Proper company names (not just symbols)
- **Add/Remove Symbols** - Interactive management with popup dialogs
- **Multi-select** - Select and delete multiple symbols at once
- **Change Tracking** - Price change percentages and volume data

### 🎛️ Data Management
- **Persistent Storage** - SQLite database for reliable data storage
- **Background Updates** - Continuous price updates every 5 seconds
- **Cache System** - Cached portfolio and account data
- **Historical Fallback** - Uses historical data when real-time is unavailable

## 🚀 Quick Start

### Prerequisites
- Interactive Brokers TWS or IB Gateway running on `host.docker.internal:7498`
- Python 3.11+ with virtual environment

### Installation

1. **Create and activate virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

### Running the Application

#### Option 1: Complete Application (Recommended)
```bash
python start.py
```
This starts both the data server and web server automatically.

#### Option 2: Individual Components
```bash
# Terminal 1: Start data server
python data_server.py

# Terminal 2: Start web server
PORT=8001 python app.py
```

### Access the Application
- **Web Interface**: http://localhost:8000 (or 8001 if using individual components)
- **Health Check**: http://localhost:8000/health

## 🔧 Development & Debugging

### VS Code Debug Configurations

Press `F5` or use **Run and Debug** panel with these configurations:

#### Primary Configurations:
- **Debug: Full Application** - Debug both data server and web server simultaneously
- **Debug: Web Server (Flask App)** - Debug only the web interface
- **Debug: Data Server** - Debug the background price fetching service
- **Debug: Complete App (Start Script)** - Debug the startup manager

#### Utility Configurations:
- **Debug: Database Operations** - Debug database initialization and operations
- **Debug: Test Watchlist** - Debug watchlist functionality
- **Attach: To Running Process** - Attach to already running processes

### Tasks (Ctrl+Shift+P → "Tasks: Run Task")
- **Start Complete App** - Launch the full application
- **Start Web Server Only** - Launch only Flask web server
- **Start Data Server Only** - Launch only the data service
- **Initialize Database** - Set up SQLite database
- **Test Watchlist Functionality** - Run watchlist tests
- **Kill All Python Processes** - Clean up running processes

### Environment Variables
```bash
PORT=8001                    # Web server port (default: 8000)
FLASK_ENV=development       # Flask environment
FLASK_DEBUG=1               # Enable Flask debugging
```

## 📁 Project Structure

```
├── app.py                  # Flask web server
├── data_server.py          # Background data fetching service
├── database.py             # SQLite database operations
├── start.py               # Application startup manager
├── ib_positions.py        # IB positions fetching (legacy/utility)
├── watchlist.py           # Legacy watchlist (deprecated)
├── test_watchlist.py      # Watchlist testing utilities
├── trading_app.db         # SQLite database (created at runtime)
├── watchlist.json         # Legacy watchlist storage (deprecated)
├── templates/             # HTML templates
│   ├── dashboard.html     # Main dashboard
│   ├── watchlist.html     # Watchlist interface
│   ├── portfolio.html     # Portfolio view
│   ├── account_info.html  # Account information
│   └── error.html         # Error page
├── .vscode/              # VS Code configurations
│   ├── launch.json       # Debug configurations
│   ├── settings.json     # Python settings
│   └── tasks.json        # Build/run tasks
└── requirements.txt       # Python dependencies
```

## 🗄️ Database Schema

### Tables
- **watchlist** - Symbol names and company information
- **price_data** - Real-time price data with timestamps
- **account_cache** - Cached account information
- **portfolio_cache** - Cached portfolio positions

## 🔌 IB TWS Configuration

### Connection Settings
- **Host**: `host.docker.internal` (for Docker) or `localhost`
- **Port**: `7498` (TWS) or `7496` (IB Gateway)
- **Client ID**: `3` (Web Server), `10` (Data Server)

### Market Data
- **Real-time**: Requires IB market data subscriptions
- **Delayed**: Free delayed data (15-20 minutes)
- **Historical**: Fallback for when market data is unavailable

### TWS Setup
1. Enable API connections in TWS
2. Set "Enable ActiveX and Socket Clients" to true
3. Add trusted IP addresses if needed
4. Ensure correct port configuration

## 🧪 Testing

### Test Components
```bash
# Test database operations
python database.py

# Add test symbols to watchlist
python test_watchlist.py

# Test IB positions (legacy)
python ib_positions.py
```

### Health Checks
```bash
# Web server health
curl http://localhost:8001/health

# Database connectivity
python -c "from database import get_watchlist; print(get_watchlist())"
```

## 📝 API Endpoints

### Web Interface
- `GET /` - Redirect to dashboard
- `GET /dashboard` - Main dashboard
- `GET /watchlist` - Watchlist interface
- `GET /portfolio` - Portfolio positions
- `GET /account` - Account information

### REST API
- `POST /api/watchlist/add` - Add symbol to watchlist
- `POST /api/watchlist/remove` - Remove symbols from watchlist
- `GET /health` - Health check endpoint

## 🚨 Troubleshooting

### Common Issues

#### "Port already in use"
```bash
# Kill existing processes
pkill -f "python.*app.py"
# Or use different port
PORT=8002 python app.py
```

#### "Cannot connect to IB"
- Ensure TWS/IB Gateway is running
- Check API settings in TWS
- Verify host/port configuration
- Try different client ID

#### "No price data"
- Check IB market data subscriptions
- Verify TWS connection in data server logs
- Historical data fallback should provide prices

#### Database Issues
```bash
# Reinitialize database
rm trading_app.db
python database.py
```

## 🔄 Data Flow

1. **Data Server** connects to IB TWS
2. Fetches real-time/historical price data
3. Updates SQLite database every 5 seconds
4. **Web Server** reads from database
5. Serves updated data to web interface
6. Users interact through browser interface

## 📦 Dependencies

### Core Requirements
- `flask==3.0.0` - Web framework
- `ib_insync==0.9.86` - IB API client
- `pandas==2.1.0` - Data manipulation

### Development
- VS Code with Python extension
- SQLite browser (optional, for database inspection)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Use VS Code debug configurations for development
4. Test with both individual components and full application
5. Submit pull request

## 📄 License

This project is for educational and personal use with Interactive Brokers API.

---

**Note**: This application requires an active Interactive Brokers account and TWS/IB Gateway installation. Market data subscriptions may be required for real-time data.```
