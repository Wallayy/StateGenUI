#!/usr/bin/env python3
"""
StateGenerator Web Server
Serves static files and provides API endpoints for biome data, entity lookup, and state generation.
"""

import http.server
import socketserver
import json
import os
import sys
import webbrowser
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import threading
import time

# Configuration
PORT = 8080
HOST = 'localhost'

# Directory structure
_APP_DIR = Path(__file__).parent
_PROJECT_ROOT = _APP_DIR.parent
_DATABASE_DIR = _PROJECT_ROOT / "database" / "data"
_SCRAPING_DIR = _PROJECT_ROOT / "database" / "scraping"
_TEMPLATES_DIR = _APP_DIR / "templates"

# Add project root to path for package imports
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Import unified data manager
try:
    from database import get_db
    _db = get_db()
    # Initialize the entity index reference for backward compatibility if needed locally,
    # but primarily use _db.entities
    stats = _db.entities.stats()
    print(f"[OK] Loaded Unified Data Manager")
    print(f"     Entities: {stats['total']}")
    print(f"     Dungeons: {len(_db.dungeons.dungeons)}")
except ImportError as e:
    _db = None
    print(f"[WARN] Database manager not available - entity search disabled: {e}")

# Import state generator
try:
    from xinjector_stategen.generators.realm_farmer import RealmFarmerConfig, generate_realm_farmer
    _generator_available = True
    print("[OK] State generator loaded")
except ImportError as e:
    _generator_available = False
    print(f"[WARN] State generator not available: {e}")


class StateGenHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for the state generator app."""

    def __init__(self, *args, **kwargs):
        # Set directory to serve templates from
        super().__init__(*args, directory=str(_TEMPLATES_DIR), **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)

        # Redirect root to state builder
        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.send_response(302)
            self.send_header('Location', '/state_builder.html')
            self.end_headers()
            return

        # Serve static assets
        if parsed_path.path.startswith('/static/'):
            self.serve_static_file(parsed_path.path)
            return

        # API endpoints
        if parsed_path.path == '/api/biomes':
            self.handle_biomes_request()
            return
        if parsed_path.path == '/api/biomes-complete':
            self.serve_database_file('biomes_complete.json')
            return
        if parsed_path.path == '/api/entities/search':
            q = query.get('q', [''])[0]
            limit = int(query.get('limit', ['20'])[0])
            self.handle_entity_search(unquote(q), limit)
            return
        if parsed_path.path == '/api/entities/lookup':
            name = query.get('name', [''])[0]
            self.handle_entity_lookup(unquote(name))
            return
        if parsed_path.path == '/api/entities/id':
            entity_id = query.get('id', ['0'])[0]
            self.handle_entity_by_id(int(entity_id))
            return
        if parsed_path.path == '/api/dungeons':
            self.handle_dungeons_request()
            return
        if parsed_path.path == '/api/dungeons-wiki':
            self.serve_database_file('dungeons_index.json')
            return
        if parsed_path.path == '/api/loot-data':
            self.serve_database_file('loot_index.json')
            return

        # Serve static files from templates
        super().do_GET()

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/export':
            self.handle_export_request()
            return
        if parsed_path.path == '/api/save-beacons':
            self.handle_save_beacons()
            return
        if parsed_path.path == '/api/generate-state':
            self.handle_generate_state()
            return
        if parsed_path.path == '/api/save-state':
            self.handle_save_state()
            return
        if parsed_path.path == '/download':
            self.handle_download()
            return

        self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def serve_static_file(self, path):
        """Serve static files from static/ directory."""
        # Remove /static/ prefix
        relative_path = path[8:]  # len('/static/') = 8
        file_path = _APP_DIR / "static" / relative_path

        if file_path.exists() and file_path.is_file():
            # Determine content type
            ext = file_path.suffix.lower()
            content_types = {
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
            }
            content_type = content_types.get(ext, 'application/octet-stream')

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()

            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"Static file not found: {path}")

    def serve_database_file(self, filename):
        """Serve a JSON file from the database/data directory."""
        try:
            file_path = _DATABASE_DIR / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_json_response(data)
            else:
                self.send_error(404, f"{filename} not found in database directory")
        except Exception as e:
            print(f"Error serving {filename}: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")

    def handle_biomes_request(self):
        """Handle request for biome data."""
        self.serve_database_file('biomes.json')

    def handle_dungeons_request(self):
        """Handle request for dungeon presets."""
        try:
            file_path = _DATABASE_DIR / 'dungeons_index.json'
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Wrap in {dungeons: data} to match frontend expectations
                self.send_json_response({'dungeons': data})
            else:
                self.send_json_response({'dungeons': {}, 'error': 'dungeons_index.json not found'})
        except Exception as e:
            print(f"Error serving dungeons: {e}")
            self.send_json_response({'dungeons': {}, 'error': str(e)}, 500)

    def handle_entity_search(self, query, limit=20):
        """Handle entity search request."""
        try:
            if not _db:
                self.send_json_response({'error': 'Entity lookup not available', 'results': []})
                return
            if not query or len(query) < 2:
                self.send_json_response({'results': []})
                return

            results = _db.entities.search(query, limit=limit)
            data = {
                'query': query,
                'results': [
                    {
                        'name': e.name,
                        'id': e.id,
                        'type': e.entity_type,
                        'dungeon': e.dungeon,
                        'biome': e.biome,
                        'drops_dungeon': e.drops_dungeon,
                    }
                    for e in results
                ]
            }
            self.send_json_response(data)
        except Exception as e:
            print(f"Error in entity search: {e}")
            self.send_json_response({'error': str(e), 'results': []})

    def handle_entity_lookup(self, name):
        """Handle entity lookup by name."""
        try:
            if not _db:
                self.send_json_response({'error': 'Entity lookup not available'})
                return

            entity = _db.entities.lookup(name)
            if entity:
                self.send_json_response({
                    'found': True,
                    'name': entity.name,
                    'id': entity.id,
                    'type': entity.entity_type,
                    'dungeon': entity.dungeon,
                    'biome': entity.biome,
                    'drops_dungeon': entity.drops_dungeon,
                    'url': entity.url
                })
            else:
                suggestions = _db.entities.search(name, limit=5)
                self.send_json_response({
                    'found': False,
                    'suggestions': [
                        {'name': e.name, 'id': e.id, 'type': e.entity_type}
                        for e in suggestions
                    ]
                })
        except Exception as e:
            print(f"Error in entity lookup: {e}")
            self.send_json_response({'error': str(e)})

    def handle_entity_by_id(self, entity_id):
        """Handle entity lookup by ID."""
        try:
            if not _db:
                self.send_json_response({'error': 'Entity lookup not available'})
                return

            entity = _db.entities.lookup_id(entity_id)
            if entity:
                self.send_json_response({
                    'found': True,
                    'name': entity.name,
                    'id': entity.id,
                    'type': entity.entity_type,
                    'dungeon': entity.dungeon,
                    'biome': entity.biome,
                    'drops_dungeon': entity.drops_dungeon,
                    'url': entity.url
                })
            else:
                self.send_json_response({'found': False, 'id': entity_id})
        except Exception as e:
            print(f"Error in entity ID lookup: {e}")
            self.send_json_response({'error': str(e)})

    def handle_generate_state(self):
        """Handle state generation request."""
        try:
            if not _generator_available:
                self.send_json_response({'error': 'State generator not available'}, 500)
                return

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({'error': 'No data provided'}, 400)
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            # Extract config fields
            config_data = data.get('_config', data)

            # Convert waypoints/positions
            waypoints = config_data.get('patrol_waypoints', [])
            if waypoints and isinstance(waypoints[0], list):
                waypoints = [tuple(pt) for pt in waypoints]

            beacon_pos = config_data.get('beacon_position', [0, 0])
            if isinstance(beacon_pos, list):
                beacon_pos = tuple(beacon_pos)

            config = RealmFarmerConfig(
                name=config_data.get('name', 'unnamed'),
                map_name=config_data.get('map_name', 'Realm of the Mad God'),
                beacon_enemy_id=config_data.get('beacon_enemy_id', 0),
                beacon_position=beacon_pos,
                beacon_distance_threshold=config_data.get('beacon_distance_threshold', 10.0),
                clear_enemy_ids=config_data.get('clear_enemy_ids', []),
                portal_id=config_data.get('portal_id'),
                portal_ids=config_data.get('portal_ids', []),
                patrol_waypoints=waypoints,
                enemy_offset_dist=config_data.get('enemy_offset_dist', 3.0),
                dungeon_map_name=config_data.get('dungeon_map_name'),
                dungeon_boss_id=config_data.get('dungeon_boss_id'),
                dungeon_additional_enemies=config_data.get('dungeon_additional_enemies')
                # dungeon_exit_portal_id defaults to 1796 (Realm Portal)
            )

            # Generate to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                temp_path = f.name

            generate_realm_farmer(config, temp_path)

            with open(temp_path, 'r') as f:
                state_json = json.load(f)

            os.unlink(temp_path)

            self.send_json_response({
                'success': True,
                'state': state_json,
                'node_count': len(state_json.get('nodes', [])),
                'link_count': len(state_json.get('links', []))
            })

            print(f"Generated state '{config.name}' with {len(state_json.get('nodes', []))} nodes")

        except Exception as e:
            import traceback
            print(f"Error generating state: {e}")
            traceback.print_exc()
            self.send_json_response({'error': str(e)}, 500)

    def handle_save_beacons(self):
        """Handle saving beacon positions."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({'error': 'No data provided'}, 400)
                return

            post_data = self.rfile.read(content_length)
            pending_changes = json.loads(post_data.decode())

            biomes_file = _DATABASE_DIR / 'biomes_complete.json'
            if not biomes_file.exists():
                self.send_json_response({'error': 'biomes_complete.json not found'}, 404)
                return

            with open(biomes_file, 'r', encoding='utf-8') as f:
                biome_data = json.load(f)

            updates_applied = 0
            for biome_id, positions in pending_changes.items():
                if biome_id in biome_data and 'beacon_positions' in biome_data[biome_id]:
                    for idx_str, new_pos in positions.items():
                        idx = int(idx_str)
                        if idx < len(biome_data[biome_id]['beacon_positions']):
                            biome_data[biome_id]['beacon_positions'][idx] = new_pos
                            updates_applied += 1

            with open(biomes_file, 'w', encoding='utf-8') as f:
                json.dump(biome_data, f, indent=2)

            self.send_json_response({
                'success': True,
                'message': f'Updated {updates_applied} beacon positions',
                'updates': updates_applied
            })

        except Exception as e:
            print(f"Error saving beacons: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def handle_export_request(self):
        """Handle export patrol points request."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'patrol_points_{timestamp}.json'
            filepath = _APP_DIR / 'exports' / filename
            filepath.parent.mkdir(exist_ok=True)

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            self.send_json_response({
                'success': True,
                'filename': filename,
                'filepath': str(filepath),
                'point_count': data.get('count', 0)
            })

        except Exception as e:
            print(f"Error handling export: {e}")
            self.send_error(500, f"Export failed: {str(e)}")

    def handle_download(self):
        """Handle file download via form POST."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        filename = data.get('filename', ['download.json'])[0]
        content = data.get('content', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def handle_save_state(self):
        """Save generated state JSON to exports folder."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({'error': 'No data provided'}, 400)
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            filename = data.get('filename', 'state.json')
            content = data.get('content', {})

            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in '._-')
            if not filename.endswith('.json'):
                filename += '.json'

            # Save to exports folder
            exports_dir = _APP_DIR / 'exports'
            exports_dir.mkdir(exist_ok=True)
            filepath = exports_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2)

            print(f"Saved state to: {filepath}")
            self.send_json_response({
                'success': True,
                'filename': filename,
                'filepath': str(filepath)
            })

        except Exception as e:
            print(f"Error saving state: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def send_json_response(self, data, status=200):
        """Helper to send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def log_message(self, format, *args):
        """Custom log message format."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")


def open_browser(url, delay=1.5):
    """Open browser after a delay."""
    time.sleep(delay)
    print(f"\nOpening browser at {url}")
    webbrowser.open(url)


def run_server():
    """Run the HTTP server."""
    os.chdir(_TEMPLATES_DIR)

    with socketserver.TCPServer((HOST, PORT), StateGenHTTPHandler) as httpd:
        url = f"http://{HOST}:{PORT}"

        print("\n" + "=" * 70)
        print("StateGenerator App - Server Started")
        print("=" * 70)
        print(f"Server running at: {url}")
        print(f"Serving from: {_TEMPLATES_DIR}")
        print("\nEndpoints:")
        print(f"  - State Builder: {url}/state_builder.html")
        print(f"  - API: {url}/api/...")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 70 + "\n")

        browser_thread = threading.Thread(target=open_browser, args=(url,))
        browser_thread.daemon = True
        browser_thread.start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down server...")


def main():
    """Main entry point."""
    try:
        run_server()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nError: Port {PORT} is already in use.")
            sys.exit(1)
        else:
            raise


if __name__ == '__main__':
    main()
