from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Flask, redirect, render_template_string, request, url_for

from .ai import MinimaxAI, SearchDiagnostics
from .board import Board, Player
from .config import GameConfig

logger = logging.getLogger(__name__)

def create_app(config: Optional[GameConfig] = None) -> Flask:
    cfg = config or GameConfig(ai_depth=int(os.getenv("CONNECTFOUR_DEPTH", 4)))
    cfg.log_config()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(cfg.log_file), logging.StreamHandler()],
    )

    app = Flask(__name__)
    app.config["cfg"] = cfg
    app.config["board"] = Board()
    app.config["ai"] = MinimaxAI(depth=cfg.ai_depth)
    app.config["last_diagnostics"] = None

    @app.route("/")
    def root() -> str:
        return redirect(url_for("play"))

    @app.route("/play", methods=["GET", "POST"])
    def play():
        board: Board = app.config["board"]
        ai: MinimaxAI = app.config["ai"]
        last_diag: Optional[SearchDiagnostics] = app.config.get("last_diagnostics")

        message = ""
        if request.method == "POST":
            try:
                col = int(request.form.get("column", ""))
            except ValueError:
                message = "Invalid move"
            else:
                if board.drop_piece(col, Player.HUMAN) is None:
                    message = "Column full or out of range"
                else:
                    over, winner = board.game_over()
                    if not over:
                        move, diagnostics = ai.choose_move(board, Player.AI)
                        board.drop_piece(move, Player.AI)
                        app.config["last_diagnostics"] = diagnostics
                        logger.info(
                            "Flask AI move",
                            extra={
                                "move": move,
                                "duration_s": diagnostics.duration_s,
                                "depth": diagnostics.search_depth,
                                "nodes": diagnostics.nodes_expanded,
                            },
                        )
                        over, winner = board.game_over()
                    else:
                        app.config["last_diagnostics"] = None
                    if over:
                        if winner is None:
                            message = "Draw!"
                        else:
                            message = f"{winner.name} wins!"
        board_rows = board.grid
        return render_template_string(
            PLAY_TEMPLATE,
            board=board_rows,
            message=message,
            last_diag=last_diag,
            cols=range(board.cols),
        )

    @app.route("/diagnostics")
    def diagnostics():
        last_diag: Optional[SearchDiagnostics] = app.config.get("last_diagnostics")
        return render_template_string(DIAGNOSTICS_TEMPLATE, diag=last_diag)

    @app.route("/reset")
    def reset():
        board: Board = app.config["board"]
        board.reset()
        app.config["last_diagnostics"] = None
        return redirect(url_for("play"))

    return app


PLAY_TEMPLATE = """
<!doctype html>
<title>Connect Four</title>
<h1>Connect Four</h1>
<p style="color: green;">{{ message }}</p>
<div style="display: grid; grid-template-columns: repeat({{ cols|length }}, 60px); gap: 6px;">
  {% for r in range(board|length) %}
    {% for c in cols %}
      {% set cell = board[r][c] %}
      {% set color = 'white' %}
      {% if cell == 1 %}{% set color = 'red' %}{% elif cell == 2 %}{% set color = 'gold' %}{% endif %}
      <div style="width: 60px; height: 60px; background: #0b61a4; display: flex; align-items: center; justify-content: center;">
        <div style="width: 48px; height: 48px; border-radius: 50%; background: {{ color }}; border: 2px solid black;"></div>
      </div>
    {% endfor %}
  {% endfor %}
</div>
<form method="post" style="margin-top: 12px;">
  <label for="column">Drop in column:</label>
  <select name="column" id="column">
    {% for c in cols %}
      <option value="{{ c }}">{{ c }}</option>
    {% endfor %}
  </select>
  <button type="submit">Play Move</button>
</form>
<p><a href="{{ url_for('reset') }}">Reset game</a> | <a href="{{ url_for('diagnostics') }}">Diagnostics</a></p>
{% if last_diag %}
  <p>AI last move depth {{ last_diag.search_depth }} in {{ '%.3f'|format(last_diag.duration_s) }}s</p>
{% endif %}
"""


DIAGNOSTICS_TEMPLATE = """
<!doctype html>
<title>Diagnostics</title>
<h1>AI Diagnostics</h1>
{% if diag %}
  <p>Search depth: {{ diag.search_depth }}</p>
  <p>Duration: {{ '%.4f'|format(diag.duration_s) }}s</p>
  <p>Nodes expanded: {{ diag.nodes_expanded }}</p>
  <h2>Evaluated moves</h2>
  <ul>
  {% for move in diag.evaluated_moves %}
    <li>Column {{ move.column }} score {{ move.score }}</li>
  {% endfor %}
  </ul>
{% else %}
  <p>No diagnostics yet. Play a game first.</p>
{% endif %}
<p><a href="{{ url_for('play') }}">Back to game</a></p>
"""


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
