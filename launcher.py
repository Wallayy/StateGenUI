#!/usr/bin/env python3
"""
StateGenerator Desktop Launcher
Launches the web app in a native desktop window using PyWebView.
"""

import sys
import threading
import time
import socket
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def find_free_port(start=8080, end=8099):
    """Find an available port in the given range."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


def start_server(port):
    """Start the HTTP server in background."""
    import http.server
    import socketserver

    # Import the handler from server.py
    from app.server import StateGenHTTPHandler, _TEMPLATES_DIR
    import os

    os.chdir(_TEMPLATES_DIR)

    # Create server with reuse address
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('localhost', port), StateGenHTTPHandler)

    print(f"[Server] Running on port {port}")
    httpd.serve_forever()


def wait_for_server(port, timeout=10):
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.1)
    return False


def main():
    """Launch the desktop application."""
    try:
        import webview
    except ImportError:
        print("ERROR: pywebview not installed.")
        print("Install with: pip install pywebview")
        sys.exit(1)

    # Find available port
    try:
        port = find_free_port()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Start server in background thread
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    print("Starting server...")
    if not wait_for_server(port):
        print("ERROR: Server failed to start")
        sys.exit(1)

    print("Server ready, launching window...")

    # Create native window
    url = f"http://localhost:{port}/state_builder.html"
    window = webview.create_window(
        title="XInjector StateGenerator",
        url=url,
        width=1400,
        height=900,
        resizable=True,
        min_size=(1024, 768),
    )

    # Start the GUI event loop (blocks until window closed)
    webview.start()

    print("Window closed, shutting down...")


if __name__ == '__main__':
    main()
