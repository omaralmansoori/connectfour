# Connect Four Toolkit

This project provides a Connect Four experience with shared game logic, a minimax-based AI opponent, a desktop GUI, and a Flask web experience that includes diagnostics for AI reasoning.

## Features
- **Core game engine** with board management, move validation, and win/draw detection.
- **Configurable AI** using minimax with alpha-beta pruning and adjustable depth.
- **Command-line interface** for quick play sessions.
- **Tkinter desktop GUI** with a visual board and user input handling.
- **Flask web app** offering a user-friendly gameplay page and an AI diagnostics page that exposes evaluated moves, search depth, timing, and nodes expanded.
- **Logging** of AI inference metrics to `connectfour.log`.

## Installation
1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Tkinter ships with most Python distributions; if missing, install it via your OS package manager.

## Package Layout
- `connectfour/board.py`: Board state, move validation, and win detection.
- `connectfour/ai.py`: Minimax AI with alpha-beta pruning and diagnostics.
- `connectfour/config.py`: Configuration helpers for AI depth and logging targets.
- `connectfour/cli.py`: CLI entry point for playing in the terminal.
- `connectfour/gui.py`: Tkinter GUI launcher.
- `connectfour/app.py`: Flask application factory and routes for gameplay and diagnostics.

## Usage
### Command Line
```bash
python -m connectfour.cli --depth 5 --human-first
```
- `--depth`: AI search depth (default: 4).
- `--human-first`: Let the human make the opening move.
- `--log-file`: Optional path for inference logs (default: `connectfour.log` in the working directory).

### Desktop GUI
```bash
python -m connectfour.gui
```
Click a column to drop a disc. Use "New Game" to reset the board. Status messages display whose turn it is and the outcome.

### Flask Web App
```bash
export FLASK_APP=connectfour.app:create_app
flask run --host=0.0.0.0 --port=8000
```
Or run directly:
```bash
python -m connectfour.app
```
- Visit `http://localhost:8000/play` to use the web UI.
- Visit `http://localhost:8000/diagnostics` to see the latest AI reasoning: evaluated moves, search depth, timing, and nodes expanded.
- Use `http://localhost:8000/reset` to start a fresh game.
- Configure AI depth via `CONNECTFOUR_DEPTH` environment variable.

## Logging
All interfaces log AI inference metrics (move chosen, duration, depth, and nodes expanded) to the log file configured in `GameConfig` (defaults to `connectfour.log`).

## Development Notes
The shared logic in `connectfour/board.py` ensures consistent rules across CLI, GUI, and Flask modes. The `MinimaxAI` in `connectfour/ai.py` provides diagnostics consumed by the Flask diagnostics page and can be reused in other frontends.
