#!/usr/bin/env python3
"""
AI Assistant Desktop - Web Only Version
Simple web server that works with any Python installation
"""

import http.server
import socketserver
import webbrowser
import threading
import time
import json
import urllib.parse
from pathlib import Path

PORT = 8080

class AIAssistantHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "web"), **kwargs)
    
    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                message = data.get('message', '')
                
                # Simple echo response
                response = {
                    'response': f"Echo: {message}",
                    'timestamp': time.time()
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_server():
    with socketserver.TCPServer(("", PORT), AIAssistantHandler) as httpd:
        print(f"🌐 AI Assistant Web Server running at http://localhost:{PORT}")
        print("🛑 Press Ctrl+C to stop")
        httpd.serve_forever()

def open_browser():
    time.sleep(2)
    webbrowser.open(f'http://localhost:{PORT}')

if __name__ == "__main__":
    print("🤖 AI Assistant Desktop - Web Only Version")
    print("=" * 50)
    
    # Start browser in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
