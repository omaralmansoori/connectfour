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

        over, winner = board.game_over()
        message = "Draw!" if over and winner is None else f"{winner.name} wins!" if winner else ""

        if request.method == "POST":
            action = request.form.get("action", "move")
            if action == "set_depth":
                try:
                    new_depth = int(request.form.get("depth", ai.depth))
                except ValueError:
                    message = "Depth must be a number between 2 and 8"
                else:
                    new_depth = max(2, min(8, new_depth))
                    cfg: GameConfig = app.config["cfg"]
                    cfg.ai_depth = new_depth
                    app.config["ai"] = MinimaxAI(depth=new_depth)
                    ai = app.config["ai"]
                    app.config["last_diagnostics"] = None
                    message = f"AI search depth set to {new_depth}. Higher depth means a slower but stronger opponent."
            elif not over:
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
                            last_diag = diagnostics
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
                            message = "Draw!" if winner is None else f"{winner.name} wins!"
        board_rows = board.grid
        return render_template_string(
            PLAY_TEMPLATE,
            board=board_rows,
            message=message,
            last_diag=last_diag,
            cols=range(board.cols),
            game_over=over,
            ai_depth=ai.depth,
        )

    @app.route("/diagnostics")
    def diagnostics():
        last_diag: Optional[SearchDiagnostics] = app.config.get("last_diagnostics")
        board: Board = app.config["board"]
        return render_template_string(
            DIAGNOSTICS_TEMPLATE,
            diag=last_diag,
            board=board.grid,
            cols=range(board.cols),
        )

    @app.route("/reset")
    def reset():
        board: Board = app.config["board"]
        board.reset()
        app.config["last_diagnostics"] = None
        return redirect(url_for("play"))

    return app


PLAY_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Connect Four Coach</title>
  <style>
    :root {
      --bg: #0c1221;
      --panel: #121b2f;
      --panel-border: #1f2a44;
      --accent: #5dd0ff;
      --accent-2: #ffb347;
      --text: #e9eef7;
      --muted: #9fb1d0;
      --human: #ff5d73;
      --ai: #ffd166;
      --shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at 20% 20%, rgba(93, 208, 255, 0.08), transparent 25%),
                  radial-gradient(circle at 80% 0%, rgba(255, 179, 71, 0.08), transparent 20%),
                  var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      padding: 32px;
    }
    h1 { margin: 0; letter-spacing: -0.5px; }
    a { color: var(--accent); }
    .page { max-width: 1200px; margin: 0 auto; }
    .top-bar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
    .subtitle { color: var(--muted); margin: 4px 0 0; }
    .badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px; background: rgba(93,208,255,0.1); color: var(--accent); font-weight: 600; font-size: 13px; }
    .layout { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 20px; margin-top: 20px; }
    .panel {
      background: linear-gradient(145deg, rgba(255,255,255,0.02), rgba(255,255,255,0));
      border: 1px solid var(--panel-border);
      border-radius: 16px;
      padding: 20px;
      box-shadow: var(--shadow);
    }
    .panel h2 { margin-top: 0; margin-bottom: 12px; font-size: 20px; }
    .board {
      background: linear-gradient(135deg, #0c5db3, #0a4f98);
      border-radius: 12px;
      padding: 12px;
      display: grid;
      grid-template-columns: repeat({{ cols|length }}, 1fr);
      gap: 10px;
      justify-content: center;
      border: 1px solid #0d3c7b;
      box-shadow: inset 0 12px 30px rgba(0,0,0,0.35);
    }
    .column {
      display: flex;
      flex-direction: column;
      gap: 10px;
      cursor: pointer;
    }
    .column.disabled {
      cursor: not-allowed;
    }
    .cell {
      width: 72px;
      height: 72px;
      background: rgba(9, 17, 35, 0.55);
      border-radius: 14px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(255,255,255,0.05);
      box-shadow: inset 0 8px 16px rgba(0,0,0,0.35);
    }
    .disc {
      width: 52px;
      height: 52px;
      border-radius: 50%;
      border: 4px solid rgba(255,255,255,0.15);
      background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.75), transparent 40%),
                  var(--muted);
      box-shadow: inset 0 6px 12px rgba(0,0,0,0.25), 0 6px 14px rgba(0,0,0,0.3);
    }
    .disc.human { background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.75), transparent 40%), var(--human); }
    .disc.ai { background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.75), transparent 40%), var(--ai); }
    form { margin: 0; }
    .controls { margin-top: 18px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
    select, input[type=number], input[type=range] {
      background: #0c162a;
      border: 1px solid var(--panel-border);
      color: var(--text);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 15px;
      min-width: 80px;
    }
    .btn {
      background: linear-gradient(135deg, var(--accent), #4ea9f9);
      color: #04101f;
      border: none;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 10px 25px rgba(93,208,255,0.35);
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .btn.secondary { background: linear-gradient(135deg, #1f2a44, #162035); color: var(--text); box-shadow: none; }
    .btn:hover { transform: translateY(-1px); box-shadow: 0 14px 30px rgba(93,208,255,0.35); }
    .status { margin-top: 14px; padding: 12px; border-radius: 12px; background: rgba(93,208,255,0.08); border: 1px solid rgba(93,208,255,0.2); color: var(--text); }
    .status.warning { background: rgba(255,93,115,0.08); border-color: rgba(255,93,115,0.2); }
    .pill-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
    .pill { background: rgba(255,255,255,0.06); border: 1px solid var(--panel-border); padding: 8px 10px; border-radius: 999px; color: var(--muted); font-size: 13px; }
    .insight-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .stat { padding: 12px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid var(--panel-border); }
    .stat .label { color: var(--muted); font-size: 13px; }
    .stat .value { font-size: 20px; font-weight: 700; margin-top: 4px; }
    details { background: rgba(255,255,255,0.03); border: 1px solid var(--panel-border); border-radius: 12px; padding: 12px; }
    details summary { cursor: pointer; font-weight: 700; }
    .tree ul { list-style: none; padding-left: 18px; margin: 6px 0; }
    .tree li { margin-bottom: 6px; }
    .tree-node { padding: 8px 10px; border-radius: 10px; background: rgba(255,255,255,0.04); border: 1px solid var(--panel-border); display: inline-flex; gap: 10px; align-items: center; }
    .legend { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 10px; color: var(--muted); }
    .legend span { display: inline-flex; align-items: center; gap: 8px; }
    .token { width: 14px; height: 14px; border-radius: 50%; display: inline-block; }
    .depth-form { margin-top: 12px; padding: 12px; border-radius: 12px; background: rgba(255,179,71,0.05); border: 1px solid rgba(255,179,71,0.2); }
    .pv { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .pv .step { padding: 6px 10px; border-radius: 10px; background: rgba(93,208,255,0.08); border: 1px solid rgba(93,208,255,0.25); color: var(--text); }
    @media (max-width: 980px) { body { padding: 20px; } .layout { grid-template-columns: 1fr; } .board { justify-content: start; } }
  </style>
</head>
<body>
  <div class=\"page\">
    <div class=\"top-bar\">
      <div>
        <h1>Connect Four AI Coach</h1>
        <p class=\"subtitle\">A classroom-ready experience for exploring minimax search. Human moves first.</p>
      </div>
      <span class=\"badge\">Learning Mode · Search tree + live board</span>
    </div>

    {% if message %}
      <div class=\"status{% if game_over %} warning{% endif %}\">{{ message }}</div>
    {% endif %}

    <div class=\"layout\">
      <div class=\"panel\">
        <div style=\"display:flex;justify-content:space-between;align-items:center;gap:12px;\">
          <h2>Game Board</h2>
          <div class=\"legend\">
            <span><span class=\"token\" style=\"background:var(--human)\"></span>Human</span>
            <span><span class=\"token\" style=\"background:var(--ai)\"></span>AI</span>
          </div>
        </div>
        <div class=\"board\">
          {% for c in cols %}
            <div class=\"column{% if game_over %} disabled{% endif %}\" onclick=\"playMove({{ c }})\">
              {% for r in range(board|length) %}
                {% set cell = board[r][c] %}
                {% set color = '' %}
                {% if cell == 1 %}{% set color = 'human' %}{% elif cell == 2 %}{% set color = 'ai' %}{% endif %}
                <div class=\"cell\">
                  <div class=\"disc {{ color }}\"></div>
                </div>
              {% endfor %}
            </div>
          {% endfor %}
        </div>
        <div class=\"controls\">
          <form id=\"moveForm\" method=\"post\" style=\"display:none;\">
            <input type=\"hidden\" name=\"action\" value=\"move\" />
            <input type=\"hidden\" name=\"column\" id=\"column\" />
          </form>
          <a href=\"{{ url_for('reset') }}\" class=\"btn secondary\">Reset</a>
          <a href=\"{{ url_for('diagnostics') }}\" class=\"btn secondary\">Diagnostics</a>
        </div>
        {% if game_over %}
          <div class=\"status warning\">Game over. Reset to start a fresh match.</div>
        {% endif %}
      </div>

      <div class=\"panel\">
        <h2>AI Insights</h2>
        <p class=\"subtitle\">Visualize the minimax search tree alongside the live board. Use depth to tune difficulty.</p>
        <div class=\"insight-grid\">
          <div class=\"stat\">
            <div class=\"label\">Search depth</div>
            <div class=\"value\">{{ ai_depth }} ply</div>
            <div class=\"pill\">Higher depth → stronger but slower AI</div>
          </div>
          <div class=\"stat\">
            <div class=\"label\">Nodes expanded</div>
            <div class=\"value\">{{ last_diag.nodes_expanded if last_diag else '—' }}</div>
            <div class=\"pill\">Each node represents a simulated future move</div>
          </div>
          <div class=\"stat\">
            <div class=\"label\">Search time</div>
            <div class=\"value\">{% if last_diag %}{{ '%.3f'|format(last_diag.duration_s) }}s{% else %}—{% endif %}</div>
            <div class=\"pill\">Timing shows compute cost of deeper searches</div>
          </div>
        </div>

        <div class=\"depth-form\">
          <form method=\"post\">
            <input type=\"hidden\" name=\"action\" value=\"set_depth\" />
            <label for=\"depth\"><strong>AI depth</strong> (2-8):</label>
            <input type=\"range\" id=\"depth\" name=\"depth\" min=\"2\" max=\"8\" value=\"{{ ai_depth }}\" oninput=\"depthValue.innerText=this.value\" />
            <div style=\"display:flex;justify-content:space-between;align-items:center;margin-top:6px;\">
              <div>Current depth: <strong id=\"depthValue\">{{ ai_depth }}</strong></div>
              <button class=\"btn\" type=\"submit\">Update difficulty</button>
            </div>
            <p class=\"subtitle\" style=\"margin-top:8px;\">Depth controls how many moves ahead the AI searches. Higher values create tougher, more deliberate play.</p>
          </form>
        </div>

        <div class=\"pill-row\">
          <span class=\"pill\">Human always starts</span>
          <span class=\"pill\">Minimax with alpha-beta pruning</span>
          <span class=\"pill\">Real-time insights for teaching</span>
        </div>

        <div style=\"margin-top: 14px;\">
          <h3 style=\"margin-bottom:6px;\">Principal variation</h3>
          {% if last_diag and last_diag.principal_variation %}
            <div class=\"pv\">
              {% for step in last_diag.principal_variation %}
                <span class=\"step\">Column {{ step }}</span>
              {% endfor %}
            </div>
          {% else %}
            <p class=\"subtitle\">Play a move to see the AI's best planned sequence.</p>
          {% endif %}
        </div>

        <details style=\"margin-top:12px;\" {% if last_diag %}open{% endif %}>
          <summary>Search tree (AI perspective)</summary>
          {% if last_diag %}
            <div class=\"tree\" style=\"margin-top:10px;\">
              {% macro render_tree(node) %}
                {% if node.children %}
                  <ul>
                    {% for child in node.children %}
                      <li>
                        <div class=\"tree-node\">
                          <span><strong>{% if child.depth == 0 %}Root{% else %}Depth {{ child.depth }}{% endif %}</strong></span>
                          <span>Column {{ child.column }}</span>
                          <span>Score {{ child.score }}</span>
                          <span>{% if child.maximizing %}AI turn{% else %}Human turn{% endif %}</span>
                        </div>
                        {{ render_tree(child) }}
                      </li>
                    {% endfor %}
                  </ul>
                {% endif %}
              {% endmacro %}
              {{ render_tree(last_diag.search_tree) }}
            </div>
          {% else %}
            <p class=\"subtitle\">No search yet. Make a move to capture the tree.</p>
          {% endif %}
        </details>
      </div>
    </div>
  </div>
  <script>
    function playMove(col) {
      if ({{ 'true' if game_over else 'false' }}) return;
      document.getElementById('column').value = col;
      document.getElementById('moveForm').submit();
    }
  </script>
</body>
</html>
"""


DIAGNOSTICS_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Diagnostics</title>
  <style>
    body { background: #0c1221; color: #e9eef7; font-family: 'Segoe UI', 'Inter', system-ui, sans-serif; padding: 28px; }
    a { color: #5dd0ff; }
    .layout { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .panel { background: rgba(255,255,255,0.04); border: 1px solid #1f2a44; border-radius: 14px; padding: 18px; }
    .board { display: grid; grid-template-columns: repeat({{ cols|length }}, 48px); gap: 8px; background: #0a4f98; padding: 10px; border-radius: 12px; }
    .cell { width: 48px; height: 48px; border-radius: 10px; background: rgba(0,0,0,0.35); display: grid; place-items: center; }
    .disc { width: 34px; height: 34px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.15); }
    .disc.human { background: #ff5d73; }
    .disc.ai { background: #ffd166; }
    .tree ul { list-style: none; padding-left: 16px; }
    .tree-node { margin: 6px 0; padding: 8px 10px; border-radius: 10px; background: rgba(255,255,255,0.05); border: 1px solid #1f2a44; }
  </style>
</head>
<body>
  <h1>Diagnostics</h1>
  <p>Use this page to review the previous AI search while keeping the final board in view.</p>
  <p><a href=\"{{ url_for('play') }}\">Back to game</a></p>
  <div class=\"layout\">
    <div class=\"panel\">
      <h2>Board snapshot</h2>
      <div class=\"board\">
        {% for r in range(board|length) %}
          {% for c in cols %}
            {% set cell = board[r][c] %}
            {% set color = '' %}
            {% if cell == 1 %}{% set color = 'human' %}{% elif cell == 2 %}{% set color = 'ai' %}{% endif %}
            <div class=\"cell\"><div class=\"disc {{ color }}\"></div></div>
          {% endfor %}
        {% endfor %}
      </div>
    </div>
    <div class=\"panel\">
      <h2>Search breakdown</h2>
      {% if diag %}
        <p>Depth: {{ diag.search_depth }} | Duration: {{ '%.3f'|format(diag.duration_s) }}s | Nodes: {{ diag.nodes_expanded }}</p>
        <h3>Evaluated root moves</h3>
        <ul>
        {% for move in diag.evaluated_moves %}
          <li>Column {{ move.column }} → score {{ move.score }}</li>
        {% endfor %}
        </ul>
        <h3>Search tree</h3>
        <div class=\"tree\">
          {% macro render_tree(node) %}
            {% if node.children %}
              <ul>
                {% for child in node.children %}
                  <li>
                    <div class=\"tree-node\">
                      Depth {{ child.depth }} · Column {{ child.column }} · Score {{ child.score }} · {% if child.maximizing %}AI{% else %}Human{% endif %} turn
                    </div>
                    {{ render_tree(child) }}
                  </li>
                {% endfor %}
              </ul>
            {% endif %}
          {% endmacro %}
          {{ render_tree(diag.search_tree) }}
        </div>
      {% else %}
        <p>No diagnostics yet. Play a game first.</p>
      {% endif %}
    </div>
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=False)
