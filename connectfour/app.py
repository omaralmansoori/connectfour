from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Flask, redirect, render_template, request, url_for

from .ai import MinimaxAI, SearchDiagnostics
from .board import Board, Player
from .checkers import CheckersBoard, evaluate_checkers
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
    app.config["diagnostics_history"] = []  # Store history of all AI decisions
    app.config["ttt_board"] = TicTacToeBoard()
    app.config["ttt_ai_depth"] = 6
    app.config["ttt_ai"] = MinimaxAI(depth=6, evaluator=evaluate_tictactoe)
    app.config["ttt_diagnostics"] = None
    app.config["ttt_last_ai_move"] = None
    app.config["ttt_diagnostics_history"] = []  # Store history for tic-tac-toe too
    app.config["checkers_board"] = CheckersBoard()
    app.config["checkers_ai_depth"] = 4
    app.config["checkers_ai"] = MinimaxAI(depth=4, evaluator=evaluate_checkers)
    app.config["checkers_turn"] = Player.HUMAN
    app.config["checkers_diagnostics"] = None
    app.config["checkers_last_ai_move"] = None
    app.config["checkers_diagnostics_history"] = []
    app.config["simulation_defaults"] = {
        "game": "connectfour",
        "depth_a": 4,
        "depth_b": 4,
        "max_turns": 64,
    }

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
                    app.config["diagnostics_history"] = []  # Clear history on depth change
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
                        # Add to history with move number and board snapshot
                        move_num = len(app.config["diagnostics_history"]) + 1
                        app.config["diagnostics_history"].append({
                            "move_num": move_num,
                            "ai_move": move,
                            "diagnostics": diagnostics,
                            "board_snapshot": [row[:] for row in board.grid]  # Deep copy
                        })
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
                                # Add to history with move number and board snapshot
                                move_num = len(app.config["diagnostics_history"]) + 1
                                app.config["diagnostics_history"].append({
                                    "move_num": move_num,
                                    "ai_move": move,
                                    "diagnostics": diagnostics,
                                    "board_snapshot": [row[:] for row in board.grid]  # Deep copy
                                })
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
        history = app.config.get("diagnostics_history", [])
        board: Board = app.config["board"]
        
        # Get selected move from query parameter, default to latest
        selected_move = request.args.get("move", type=int)
        
        if history:
            if selected_move is None or selected_move < 1 or selected_move > len(history):
                selected_move = len(history)  # Default to latest move
            
            selected_entry = history[selected_move - 1]
            diag = selected_entry["diagnostics"]
            board_snapshot = selected_entry["board_snapshot"]
        else:
            diag = app.config.get("last_diagnostics")
            board_snapshot = board.grid
            selected_move = None
        
        return render_template(
            "analysis.html",
            diag=diag,
            board=board_snapshot,
            cols=range(board.cols),
            history=history,
            selected_move=selected_move,
            total_moves=len(history),
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
                    app.config["ttt_diagnostics_history"] = []  # Clear history on depth change
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
                    # Add to history with move number and board snapshot
                    move_num = len(app.config["ttt_diagnostics_history"]) + 1
                    app.config["ttt_diagnostics_history"].append({
                        "move_num": move_num,
                        "ai_move": move,
                        "diagnostics": diagnostics,
                        "board_snapshot": [row[:] for row in board.grid]  # Deep copy
                    })
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
                            # Add to history with move number and board snapshot
                            move_num = len(app.config["ttt_diagnostics_history"]) + 1
                            app.config["ttt_diagnostics_history"].append({
                                "move_num": move_num,
                                "ai_move": ai_move,
                                "diagnostics": diagnostics,
                                "board_snapshot": [row[:] for row in board.grid]  # Deep copy
                            })
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

    @app.route("/tictactoe/analysis")
    def tictactoe_analysis():
        history = app.config.get("ttt_diagnostics_history", [])
        board: TicTacToeBoard = app.config["ttt_board"]
        
        # Get selected move from query parameter, default to latest
        selected_move = request.args.get("move", type=int)
        
        if history:
            if selected_move is None or selected_move < 1 or selected_move > len(history):
                selected_move = len(history)  # Default to latest move
            
            selected_entry = history[selected_move - 1]
            diag = selected_entry["diagnostics"]
            board_snapshot = selected_entry["board_snapshot"]
        else:
            diag = app.config.get("ttt_diagnostics")
            board_snapshot = board.grid
            selected_move = None
        
        return render_template(
            "tictactoe_analysis.html",
            diag=diag,
            board=board_snapshot,
            size=board.rows,
            history=history,
            selected_move=selected_move,
            total_moves=len(history),
        )

    @app.route("/tictactoe/reset")
    def tictactoe_reset():
        board: TicTacToeBoard = app.config["ttt_board"]
        board.reset()
        app.config["ttt_diagnostics"] = None
        app.config["ttt_last_ai_move"] = None
        app.config["ttt_diagnostics_history"] = []  # Clear history on reset
        return redirect(url_for("tictactoe"))

    @app.route("/checkers", methods=["GET", "POST"])
    def checkers():
        board: CheckersBoard = app.config["checkers_board"]
        ai: MinimaxAI = app.config["checkers_ai"]
        last_diag: Optional[SearchDiagnostics] = app.config.get("checkers_diagnostics")
        turn: Player = app.config["checkers_turn"]

        over, winner = board.game_over()
        message = "Draw!" if over and winner is None else f"{winner.name} wins!" if winner else ""

        if request.method == "POST":
            action = request.form.get("action", "move")

            if action == "set_depth":
                try:
                    new_depth = int(request.form.get("depth", ai.depth))
                except ValueError:
                    message = "Depth must be a number between 2 and 6"
                else:
                    new_depth = max(2, min(6, new_depth))
                    app.config["checkers_ai_depth"] = new_depth
                    app.config["checkers_ai"] = MinimaxAI(depth=new_depth, evaluator=evaluate_checkers)
                    ai = app.config["checkers_ai"]
                    app.config["checkers_diagnostics"] = None
                    app.config["checkers_diagnostics_history"] = []
                    message = "Updated Checkers AI depth. Higher depth explores more jumps and trades."
            elif action == "ai_start":
                if not board.is_initial() or turn != Player.HUMAN:
                    message = "Game already in progress"
                else:
                    move, diagnostics = ai.choose_move(board, Player.AI)
                    result_ai = board.drop_piece(move, Player.AI)
                    if result_ai:
                        app.config["checkers_last_ai_move"] = (result_ai.row, result_ai.col)
                    app.config["checkers_diagnostics"] = diagnostics
                    move_num = len(app.config["checkers_diagnostics_history"]) + 1
                    app.config["checkers_diagnostics_history"].append(
                        {
                            "move_num": move_num,
                            "ai_move": move,
                            "diagnostics": diagnostics,
                            "board_snapshot": [row[:] for row in board.grid],
                        }
                    )
                    last_diag = diagnostics
                    turn = Player.HUMAN
                    app.config["checkers_turn"] = Player.HUMAN
                    logger.info(
                        "Checkers AI start move",
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
            elif action == "move" and not over and turn == Player.HUMAN:
                valid_moves = board.valid_moves(Player.HUMAN)
                try:
                    move_idx = int(request.form.get("move_index", "-1"))
                except ValueError:
                    message = "Select a move to play."
                else:
                    if move_idx < 0 or move_idx >= len(valid_moves):
                        message = "That move is no longer available."
                    else:
                        move = valid_moves[move_idx]
                        app.config["checkers_last_ai_move"] = None
                        board.drop_piece(move, Player.HUMAN)
                        app.config["checkers_turn"] = Player.AI
                        over, winner = board.game_over()
                        if over:
                            message = "Draw!" if winner is None else f"{winner.name} wins!"
                        else:
                            ai_move, diagnostics = ai.choose_move(board, Player.AI)
                            result_ai = board.drop_piece(ai_move, Player.AI)
                            if result_ai:
                                app.config["checkers_last_ai_move"] = (result_ai.row, result_ai.col)
                            app.config["checkers_diagnostics"] = diagnostics
                            move_num = len(app.config["checkers_diagnostics_history"]) + 1
                            app.config["checkers_diagnostics_history"].append(
                                {
                                    "move_num": move_num,
                                    "ai_move": ai_move,
                                    "diagnostics": diagnostics,
                                    "board_snapshot": [row[:] for row in board.grid],
                                }
                            )
                            last_diag = diagnostics
                            app.config["checkers_turn"] = Player.HUMAN
                            logger.info(
                                "Checkers AI move",
                                extra={
                                    "move": ai_move,
                                    "duration_s": diagnostics.duration_s,
                                    "depth": diagnostics.search_depth,
                                    "nodes": diagnostics.nodes_expanded,
                                },
                            )
                            over, winner = board.game_over()
                            if over:
                                message = "Draw!" if winner is None else f"{winner.name} wins!"

        human_moves = board.valid_moves(Player.HUMAN)
        return render_template(
            "checkers.html",
            board=board.grid,
            human_moves=human_moves,
            message=message,
            game_over=over,
            last_diag=last_diag,
            ai_depth=app.config["checkers_ai_depth"],
            turn=app.config["checkers_turn"],
            human_turn=app.config["checkers_turn"] == Player.HUMAN,
            last_ai_move=app.config.get("checkers_last_ai_move"),
        )

    @app.route("/checkers/analysis")
    def checkers_analysis():
        history = app.config.get("checkers_diagnostics_history", [])
        board: CheckersBoard = app.config["checkers_board"]

        selected_move = request.args.get("move", type=int)

        if history:
            if selected_move is None or selected_move < 1 or selected_move > len(history):
                selected_move = len(history)

            selected_entry = history[selected_move - 1]
            diag = selected_entry["diagnostics"]
            board_snapshot = selected_entry["board_snapshot"]
        else:
            diag = app.config.get("checkers_diagnostics")
            board_snapshot = board.grid
            selected_move = None

        return render_template(
            "checkers_analysis.html",
            diag=diag,
            board=board_snapshot,
            history=history,
            selected_move=selected_move,
            total_moves=len(history),
        )

    @app.route("/checkers/reset")
    def checkers_reset():
        board: CheckersBoard = app.config["checkers_board"]
        board.reset()
        app.config["checkers_turn"] = Player.HUMAN
        app.config["checkers_diagnostics"] = None
        app.config["checkers_last_ai_move"] = None
        app.config["checkers_diagnostics_history"] = []
        return redirect(url_for("checkers"))

    @app.route("/simulate", methods=["GET", "POST"])
    def simulate():
        defaults = app.config["simulation_defaults"]
        selected_game = request.form.get("game", defaults["game"]) if request.method == "POST" else defaults["game"]
        depth_a = request.form.get("depth_a", defaults["depth_a"])
        depth_b = request.form.get("depth_b", defaults["depth_b"])
        max_turns = request.form.get("max_turns", defaults["max_turns"])
        error = None
        result = None

        def game_factory(game: str):
            if game == "connectfour":
                return Board(), MinimaxAI, None
            if game == "tictactoe":
                return TicTacToeBoard(), MinimaxAI, evaluate_tictactoe
            if game == "checkers":
                return CheckersBoard(), MinimaxAI, evaluate_checkers
            raise ValueError("Unknown game type")

        def describe_move(game: str, move, board_rows: int, board_cols: int) -> str:
            if game == "connectfour":
                return f"Column {move}"
            if game == "tictactoe":
                row, col = divmod(int(move), board_cols)
                return f"Cell ({row}, {col})"
            if game == "checkers":
                path = getattr(move, "path", [])
                captures = getattr(move, "captures", [])
                path_str = " → ".join(f"({r},{c})" for r, c in path)
                capture_info = f" | captures {len(captures)}" if captures else ""
                return f"Path {path_str}{capture_info}" if path_str else "Checkers move"
            return "Move"

        def simulate_game(game: str, d_a: int, d_b: int, limit: int):
            board, ai_cls, evaluator = game_factory(game)
            ai_a = ai_cls(depth=d_a, evaluator=evaluator)
            ai_b = ai_cls(depth=d_b, evaluator=evaluator)
            move_history = []
            total_nodes = 0
            total_time = 0.0
            over, winner = board.game_over()
            for turn in range(limit):
                if over:
                    break
                player = Player.HUMAN if turn % 2 == 0 else Player.AI
                active_ai = ai_a if player == Player.HUMAN else ai_b
                move, diag = active_ai.choose_move(board, player)
                placed = board.drop_piece(move, player)
                if placed is None:
                    error_msg = f"AI attempted invalid move on turn {turn + 1}."
                    return None, error_msg
                move_history.append(
                    {
                        "turn": turn + 1,
                        "player": "AI A" if player == Player.HUMAN else "AI B",
                        "as_player": player.name,
                        "move": describe_move(game, move, board.rows, board.cols),
                        "diagnostics": diag,
                        "board_snapshot": [row[:] for row in board.grid],
                    }
                )
                total_nodes += diag.nodes_expanded
                total_time += diag.duration_s
                over, winner = board.game_over()

            summary = {
                "game": game,
                "rows": board.rows,
                "cols": board.cols,
                "history": move_history,
                "over": over,
                "winner": winner,
                "final_board": board.grid,
                "total_nodes": total_nodes,
                "total_time": total_time,
                "max_turns_hit": len(move_history) >= limit and not over,
                "depth_a": d_a,
                "depth_b": d_b,
            }
            return summary, None

        if request.method == "POST":
            try:
                depth_a_val = max(1, min(10, int(depth_a)))
                depth_b_val = max(1, min(10, int(depth_b)))
                max_turns_val = max(4, min(200, int(max_turns)))
            except ValueError:
                error = "Depth and turn limit must be numbers."
            else:
                result, error = simulate_game(selected_game, depth_a_val, depth_b_val, max_turns_val)
                depth_a = depth_a_val
                depth_b = depth_b_val
                max_turns = max_turns_val
                defaults.update(
                    {"game": selected_game, "depth_a": depth_a, "depth_b": depth_b, "max_turns": max_turns}
                )

        analysis_text = None
        if result:
            if result["winner"] is None:
                verdict = "It was a draw—did the shallower AI hold its own?"
            else:
                victor = "AI A" if result["winner"] == Player.HUMAN else "AI B"
                verdict = f"{victor} prevailed while playing as {result['winner'].name}."
            depth_note = "Both AIs searched equally deep." if depth_a == depth_b else (
                "AI A searched deeper." if depth_a > depth_b else "AI B searched deeper."
            )
            efficiency = f"Across {len(result['history'])} plies they expanded {result['total_nodes']} nodes in {result['total_time']:.3f}s."
            analysis_text = f"{verdict} {depth_note} {efficiency}"

        return render_template(
            "simulate.html",
            selected_game=selected_game,
            depth_a=depth_a,
            depth_b=depth_b,
            max_turns=max_turns,
            result=result,
            error=error,
            analysis_text=analysis_text,
        )

    @app.route("/reset")
    def reset():
        board: Board = app.config["board"]
        board.reset()
        app.config["last_diagnostics"] = None
        app.config["last_ai_move"] = None
        app.config["diagnostics_history"] = []  # Clear history on reset
        return redirect(url_for("play"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=False)
