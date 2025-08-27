#!/usr/bin/env python3
"""
Startup script for the trading application
Starts both data server and web server
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

class ApplicationManager:
    def __init__(self):
        self.data_server_process = None
        self.web_server_process = None
        self.running = True
        
    def cleanup(self, signum=None, frame=None):
        """Cleanup background processes"""
        print("\nShutting down...")
        
        if self.data_server_process:
            try:
                self.data_server_process.terminate()
                self.data_server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.data_server_process.kill()
            except Exception as e:
                print(f"Error stopping data server: {e}")
        
        if self.web_server_process:
            try:
                self.web_server_process.terminate() 
                self.web_server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.web_server_process.kill()
            except Exception as e:
                print(f"Error stopping web server: {e}")
        
        self.running = False
        print("Application stopped successfully")
        sys.exit(0)
    
    def start(self):
        """Start the trading application"""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        print("Starting Trading Application...")
        
        # Get Python executable path
        python_path = sys.executable
        
        # Initialize database
        print("Initializing database...")
        try:
            result = subprocess.run([python_path, 'database.py'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"Database initialization failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False
        
        # Start data server
        print("Starting data server...")
        try:
            self.data_server_process = subprocess.Popen(
                [python_path, 'data_server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            print(f"Data server started (PID: {self.data_server_process.pid})")
        except Exception as e:
            print(f"Error starting data server: {e}")
            return False
        
        # Wait a few seconds for data server to initialize
        time.sleep(3)
        
        # Check if data server is still running
        if self.data_server_process.poll() is not None:
            print("Data server failed to start")
            return False
        
        # Start web server
        print("Starting web server...")
        try:
            self.web_server_process = subprocess.Popen(
                [python_path, 'app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            print(f"Web server started (PID: {self.web_server_process.pid})")
        except Exception as e:
            print(f"Error starting web server: {e}")
            self.cleanup()
            return False
        
        print("Trading application started successfully!")
        print("Web interface available at: http://localhost:8000")
        print("Press Ctrl+C to stop all servers")
        
        # Monitor processes
        try:
            while self.running:
                # Check if processes are still running
                if self.data_server_process and self.data_server_process.poll() is not None:
                    print("Data server has stopped unexpectedly")
                    break
                    
                if self.web_server_process and self.web_server_process.poll() is not None:
                    print("Web server has stopped unexpectedly")
                    break
                
                # Read and display output from data server
                if self.data_server_process and self.data_server_process.stdout:
                    try:
                        line = self.data_server_process.stdout.readline()
                        if line:
                            print(f"[DATA SERVER] {line.strip()}")
                    except Exception:
                        pass
                
                # Read and display output from web server (less frequent)
                if self.web_server_process and self.web_server_process.stdout:
                    try:
                        line = self.web_server_process.stdout.readline()
                        if line:
                            print(f"[WEB SERVER] {line.strip()}")
                    except Exception:
                        pass
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
        
        return True

if __name__ == '__main__':
    app_manager = ApplicationManager()
    success = app_manager.start()
    sys.exit(0 if success else 1)
