#!/usr/bin/env python3
"""
Local development server for testing the Menu Translator
Serves index.html and routes /api/menu to the Menu handler
"""
import os
import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from datetime import datetime

# Load environment variables from .env file
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✓ Loaded .env file")
    else:
        print("⚠️  .env file not found - API key may not be available")

# Add api directory to path
sys.path.insert(0, str(Path(__file__).parent / "api"))
from menu import handler as MenuHandler

class LocalDevHandler(SimpleHTTPRequestHandler):
    """Custom handler that routes API calls and serves static files"""

    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        # Route API calls to the Menu handler
        if self.path == '/api/menu':
            # Log request details
            content_length = self.headers.get('Content-Length', 0)
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n{'='*60}")
            print(f"[{timestamp}] 🔵 API POST /api/menu")
            print(f"{'='*60}")
            print(f"📦 Request size: {content_length} bytes")
            print(f"🔑 Content-Type: {self.headers.get('Content-Type', 'N/A')}")
            print(f"⏱️  Processing request...")

            # Create a Menu handler instance and delegate
            menu_handler = MenuHandler(self.request, self.client_address, self.server)
            menu_handler.headers = self.headers
            menu_handler.rfile = self.rfile
            menu_handler.wfile = self.wfile
            menu_handler.do_POST()

            print(f"✅ Request completed at {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}\n")
        else:
            self.send_error(404, f"Endpoint not found: {self.path}")

    def do_OPTIONS(self):
        # Handle CORS preflight for API calls
        if self.path.startswith('/api/'):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        # Custom log format with timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        if self.path.startswith('/api/'):
            # API calls are logged in detail by do_POST, skip here
            pass
        else:
            print(f"[{timestamp}] 📄 {self.command} {self.path}")

def main():
    # Load environment variables
    load_env()

    # Check for API key
    if not os.environ.get('GEMINI_API_KEY'):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment")
        print("   The API calls will fail without a valid API key")
        print()

    # Start server
    PORT = 8000
    server_address = ('', PORT)

    print("\n" + "="*60)
    print("🚀 Local Development Server Starting...")
    print("="*60)
    print(f"\n📍 Server running at: http://localhost:{PORT}")
    print(f"📄 Frontend: http://localhost:{PORT}/")
    print(f"🔌 API endpoint: http://localhost:{PORT}/api/menu")
    print("\n" + "="*60)
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")

    httpd = HTTPServer(server_address, LocalDevHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 Server stopped")
        print("="*60 + "\n")
        httpd.shutdown()

if __name__ == "__main__":
    main()
