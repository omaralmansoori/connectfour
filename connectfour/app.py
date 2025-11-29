from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Flask, redirect, render_template, request, url_for

from .ai import MinimaxAI, SearchDiagnostics
from .board import Board, Player
from .config import GameConfig
from .tictactoe import TicTacToeBoard, evaluate_tictactoe

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
    app.config["last_ai_move"] = None
    app.config["ttt_board"] = TicTacToeBoard()
    app.config["ttt_ai_depth"] = 6
    app.config["ttt_ai"] = MinimaxAI(depth=6, evaluator=evaluate_tictactoe)
    app.config["ttt_diagnostics"] = None
    app.config["ttt_last_ai_move"] = None

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
                # allow AI to make the first move when requested
                if action == "ai_start":
                    # only allow if the board is empty
                    if any(cell != 0 for row in board.grid for cell in row):
                        message = "Game already in progress"
                    else:
                        move, diagnostics = ai.choose_move(board, Player.AI)
                        result_ai = board.drop_piece(move, Player.AI)
                        if result_ai:
                            app.config["last_ai_move"] = (result_ai.row, result_ai.col)
                        app.config["last_diagnostics"] = diagnostics
                        last_diag = diagnostics
                        logger.info(
                            "Flask AI start move",
                            extra={
                                "move": move,
                                "duration_s": diagnostics.duration_s,
                                "depth": diagnostics.search_depth,
                                "nodes": diagnostics.nodes_expanded,
                            },
                        )
                        over, winner = board.game_over()
                        if over:
                            message = "Draw!" if winner is None else f"{winner.name} wins!"
                    # skip human move handling below
                    # fall through to rendering
                else:
                    try:
                        col = int(request.form.get("column", ""))
                    except ValueError:
                        message = "Invalid move"
                    else:
                        result = board.drop_piece(col, Player.HUMAN)
                        if result is None:
                            message = "Column full or out of range"
                        else:
                            app.config["last_ai_move"] = None  # clear previous AI move highlight
                            over, winner = board.game_over()
                            if not over:
                                move, diagnostics = ai.choose_move(board, Player.AI)
                                result_ai = board.drop_piece(move, Player.AI)
                                if result_ai:
                                    app.config["last_ai_move"] = (result_ai.row, result_ai.col)
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
        return render_template(
            "play.html",
            board=board_rows,
            message=message,
            last_diag=last_diag,
            cols=range(board.cols),
            game_over=over,
            ai_depth=ai.depth,
            last_ai_move=app.config.get("last_ai_move"),
        )

    @app.route("/analysis")
    def analysis():
        last_diag: Optional[SearchDiagnostics] = app.config.get("last_diagnostics")
        board: Board = app.config["board"]
        return render_template(
            "analysis.html",
            diag=last_diag,
            board=board.grid,
            cols=range(board.cols),
        )

    @app.route("/learn")
    def learn():
        return render_template("learn.html")

    @app.route("/tictactoe", methods=["GET", "POST"])
    def tictactoe():
        board: TicTacToeBoard = app.config["ttt_board"]
        ai: MinimaxAI = app.config["ttt_ai"]
        last_diag: Optional[SearchDiagnostics] = app.config.get("ttt_diagnostics")

        over, winner = board.game_over()
        message = "Draw!" if over and winner is None else f"{winner.name} wins!" if winner else ""

        if request.method == "POST":
            action = request.form.get("action", "move")

            if action == "set_depth":
                try:
                    new_depth = int(request.form.get("depth", ai.depth))
                except ValueError:
                    message = "Depth must be a number between 2 and 9"
                else:
                    new_depth = max(2, min(9, new_depth))
                    app.config["ttt_ai_depth"] = new_depth
                    app.config["ttt_ai"] = MinimaxAI(depth=new_depth, evaluator=evaluate_tictactoe)
                    ai = app.config["ttt_ai"]
                    app.config["ttt_diagnostics"] = None
                    message = "Updated Tic-Tac-Toe depth. Max depth explores the full game tree."
            elif action == "ai_start":
                if not board.is_empty():
                    message = "Game already in progress"
                else:
                    move, diagnostics = ai.choose_move(board, Player.AI)
                    result_ai = board.drop_piece(move, Player.AI)
                    if result_ai:
                        app.config["ttt_last_ai_move"] = (result_ai.row, result_ai.col)
                    app.config["ttt_diagnostics"] = diagnostics
                    last_diag = diagnostics
                    logger.info(
                        "TicTacToe AI start move",
                        extra={
                            "move": move,
                            "duration_s": diagnostics.duration_s,
                            "depth": diagnostics.search_depth,
                            "nodes": diagnostics.nodes_expanded,
                        },
                    )
                    over, winner = board.game_over()
                    if over:
                        message = "Draw!" if winner is None else f"{winner.name} wins!"
            elif not over:
                try:
                    move = int(request.form.get("move", ""))
                except ValueError:
                    message = "Invalid move"
                else:
                    result = board.drop_piece(move, Player.HUMAN)
                    if result is None:
                        message = "Cell already taken."
                    else:
                        app.config["ttt_last_ai_move"] = None
                        over, winner = board.game_over()
                        if not over:
                            ai_move, diagnostics = ai.choose_move(board, Player.AI)
                            result_ai = board.drop_piece(ai_move, Player.AI)
                            if result_ai:
                                app.config["ttt_last_ai_move"] = (result_ai.row, result_ai.col)
                            app.config["ttt_diagnostics"] = diagnostics
                            last_diag = diagnostics
                            logger.info(
                                "TicTacToe AI move",
                                extra={
                                    "move": ai_move,
                                    "duration_s": diagnostics.duration_s,
                                    "depth": diagnostics.search_depth,
                                    "nodes": diagnostics.nodes_expanded,
                                },
                            )
                            over, winner = board.game_over()
                        else:
                            app.config["ttt_diagnostics"] = None
                        if over:
                            message = "Draw!" if winner is None else f"{winner.name} wins!"

        return render_template(
            "tictactoe.html",
            board=board.grid,
            message=message,
            game_over=over,
            last_diag=last_diag,
            ai_depth=app.config["ttt_ai_depth"],
            last_ai_move=app.config.get("ttt_last_ai_move"),
            size=board.rows,
        )

    @app.route("/tictactoe/reset")
    def tictactoe_reset():
        board: TicTacToeBoard = app.config["ttt_board"]
        board.reset()
        app.config["ttt_diagnostics"] = None
        app.config["ttt_last_ai_move"] = None
        return redirect(url_for("tictactoe"))

    @app.route("/reset")
    def reset():
        board: Board = app.config["board"]
        board.reset()
        app.config["last_diagnostics"] = None
        app.config["last_ai_move"] = None
        return redirect(url_for("play"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=False)
