# XInjector StateGenerator

Visual workflow builder for XInjector state machine JSON files. Create DAG-based automation workflows through an interactive map interface.

## Installation

### Option 1: Download Executable (Easiest)
Download `StateGenerator.exe` from Releases. Double-click to run - no installation needed.

### Option 2: Run from Source

```bash
# Clone the repo
git clone https://github.com/yourusername/StateGenerator_app.git
cd StateGenerator_app

# Install dependencies
pip install -e .

# Run the app (opens in native window)
python launcher.py

# Or on Windows, double-click:
run.bat
```

## Building from Source

See [BUILD.md](BUILD.md) for creating standalone executables.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Build single .exe
python build.py
```

## Project Structure

```
StateGenerator_app/
├── launcher.py            # Desktop app launcher (PyWebView)
├── app/                   # Web application
│   ├── server.py          # HTTP server
│   ├── static/            # CSS, JS, images
│   └── templates/         # HTML (state_builder.html)
├── xinjector_stategen/    # Core Python package
│   ├── dag/               # StateGenerator + primitives
│   ├── patterns/          # Reusable workflow patterns
│   └── generators/        # High-level generators
├── database/
│   ├── data/              # Biome/dungeon JSON data
│   └── scraping/          # Entity lookup cache
└── docs/                  # Documentation
```

## Development

| Task | Location |
|------|----------|
| Generator logic | `xinjector_stategen/` |
| Web UI | `app/templates/state_builder.html` |
| Server endpoints | `app/server.py` |
| Entity data | `database/data/` |

## Requirements

- Python 3.9+ (for running from source)
- Windows 10/11 (for executable)
- WebView2 Runtime (usually pre-installed on Windows 10+)
