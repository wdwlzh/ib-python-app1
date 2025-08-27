#!/usr/bin/env python3
"""
Development startup script with real-time logs
Shows output from both data server and web server in real-time
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

class LogReader:
    def __init__(self, process, prefix):
        self.process = process
        self.prefix = prefix
        self.thread = None
        self.running = False
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_output)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _read_output(self):
        while self.running and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    print(f"{self.prefix} {line.rstrip()}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"{self.prefix} Error reading output: {e}")
                break

class DevelopmentManager:
    def __init__(self):
        self.data_server_process = None
        self.web_server_process = None
        self.data_reader = None
        self.web_reader = None
        self.running = True
        
    def cleanup(self, signum=None, frame=None):
        """Cleanup background processes"""
        print("\n🛑 Shutting down...")
        self.running = False
        
        # Stop log readers
        if self.data_reader:
            self.data_reader.stop()
        if self.web_reader:
            self.web_reader.stop()
        
        # Stop processes
        if self.data_server_process:
            try:
                self.data_server_process.terminate()
                self.data_server_process.wait(timeout=5)
                print("✅ Data server stopped")
            except subprocess.TimeoutExpired:
                self.data_server_process.kill()
                print("💀 Data server killed (forced)")
            except Exception as e:
                print(f"❌ Error stopping data server: {e}")
        
        if self.web_server_process:
            try:
                self.web_server_process.terminate() 
                self.web_server_process.wait(timeout=5)
                print("✅ Web server stopped")
            except subprocess.TimeoutExpired:
                self.web_server_process.kill()
                print("💀 Web server killed (forced)")
            except Exception as e:
                print(f"❌ Error stopping web server: {e}")
        
        print("🎯 Application stopped successfully")
        sys.exit(0)
    
    def start(self):
        """Start the trading application with real-time logs"""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        print("🚀 Starting Trading Application (Development Mode)...")
        print("📋 Real-time logs will be displayed below")
        print("🔄 Press Ctrl+C to stop all servers\n")
        
        # Get Python executable path
        python_path = sys.executable
        
        # Initialize database
        print("🗄️  Initializing database...")
        try:
            result = subprocess.run([python_path, 'database.py'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"❌ Database initialization failed: {result.stderr}")
                return False
            print("✅ Database initialized\n")
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            return False
        
        # Start data server
        print("📊 Starting data server...")
        try:
            self.data_server_process = subprocess.Popen(
                [python_path, 'data_server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            print(f"✅ Data server started (PID: {self.data_server_process.pid})")
            
            # Start log reader for data server
            self.data_reader = LogReader(self.data_server_process, "📊 [DATA]")
            self.data_reader.start()
            
        except Exception as e:
            print(f"❌ Error starting data server: {e}")
            return False
        
        # Wait a few seconds for data server to initialize
        print("⏳ Waiting for data server to initialize...")
        time.sleep(3)
        
        # Check if data server is still running
        if self.data_server_process.poll() is not None:
            print("❌ Data server failed to start")
            return False
        
        # Start web server
        print("🌐 Starting web server...")
        try:
            env = os.environ.copy()
            env['PORT'] = '8001'
            env['FLASK_ENV'] = 'development'
            
            self.web_server_process = subprocess.Popen(
                [python_path, 'app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env
            )
            print(f"✅ Web server started (PID: {self.web_server_process.pid})")
            
            # Start log reader for web server
            self.web_reader = LogReader(self.web_server_process, "🌐 [WEB] ")
            self.web_reader.start()
            
        except Exception as e:
            print(f"❌ Error starting web server: {e}")
            self.cleanup()
            return False
        
        print("\n🎉 Trading application started successfully!")
        print("🌐 Web interface: http://localhost:8001")
        print("💚 Health check: http://localhost:8001/health")
        print("📋 Live logs shown below:")
        print("=" * 60)
        
        # Monitor processes
        try:
            while self.running:
                # Check if processes are still running
                if self.data_server_process and self.data_server_process.poll() is not None:
                    print("💥 Data server has stopped unexpectedly")
                    break
                    
                if self.web_server_process and self.web_server_process.poll() is not None:
                    print("💥 Web server has stopped unexpectedly")
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
        
        return True

if __name__ == '__main__':
    app_manager = DevelopmentManager()
    success = app_manager.start()
    sys.exit(0 if success else 1)
