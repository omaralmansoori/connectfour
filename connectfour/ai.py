from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .board import Board, Player

logger = logging.getLogger(__name__)


@dataclass
class MoveEvaluation:
    column: int
    score: int


@dataclass
class SearchDiagnostics:
    evaluated_moves: List[MoveEvaluation]
    search_depth: int
    duration_s: float
    nodes_expanded: int


class MinimaxAI:
    def __init__(self, depth: int = 4) -> None:
        self.depth = depth

    def choose_move(self, board: Board, player: Player = Player.AI) -> Tuple[int, SearchDiagnostics]:
        start = time.perf_counter()
        evaluations: List[MoveEvaluation] = []
        nodes_expanded = 0

        def minimax(state: Board, depth: int, maximizing: bool, alpha: float, beta: float) -> Tuple[int, Optional[int]]:
            nonlocal nodes_expanded
            nodes_expanded += 1
            game_over, winner = state.game_over()
            if depth == 0 or game_over:
                return self.evaluate_board(state, player), None

            valid = state.valid_moves()
            if maximizing:
                value = -float("inf")
                best_move: Optional[int] = None
                for col in valid:
                    child = state.clone()
                    child.drop_piece(col, player)
                    score, _ = minimax(child, depth - 1, False, alpha, beta)
                    if depth == self.depth:
                        evaluations.append(MoveEvaluation(column=col, score=score))
                    if score > value:
                        value = score
                        best_move = col
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break
                return int(value), best_move
            else:
                value = float("inf")
                best_move = None
                opp = Player.HUMAN if player == Player.AI else Player.AI
                for col in valid:
                    child = state.clone()
                    child.drop_piece(col, opp)
                    score, _ = minimax(child, depth - 1, True, alpha, beta)
                    if score < value:
                        value = score
                        best_move = col
                    beta = min(beta, value)
                    if alpha >= beta:
                        break
                return int(value), best_move

        score, move = minimax(board, self.depth, True, -float("inf"), float("inf"))
        duration = time.perf_counter() - start
        if move is None:
            valid_moves = board.valid_moves()
            move = valid_moves[0] if valid_moves else -1
        diagnostics = SearchDiagnostics(
            evaluated_moves=evaluations,
            search_depth=self.depth,
            duration_s=duration,
            nodes_expanded=nodes_expanded,
        )
        logger.info(
            "AI move computed", extra={
                "search_depth": diagnostics.search_depth,
                "duration": diagnostics.duration_s,
                "nodes_expanded": diagnostics.nodes_expanded,
                "best_score": score,
                "best_move": move,
            },
        )
        return move, diagnostics

    def evaluate_board(self, board: Board, player: Player) -> int:
        opponent = Player.HUMAN if player == Player.AI else Player.AI
        return self.score_position(board, player) - self.score_position(board, opponent)

    def score_position(self, board: Board, player: Player) -> int:
        grid = board.grid
        score = 0
        center_col = [grid[r][board.cols // 2] for r in range(board.rows)]
        score += center_col.count(int(player)) * 3

        def evaluate_window(window: List[int]) -> int:
            score_window = 0
            token = int(player)
            opp = int(Player.HUMAN if player == Player.AI else Player.AI)
            if window.count(token) == 4:
                score_window += 100
            elif window.count(token) == 3 and window.count(0) == 1:
                score_window += 5
            elif window.count(token) == 2 and window.count(0) == 2:
                score_window += 2
            if window.count(opp) == 3 and window.count(0) == 1:
                score_window -= 4
            return score_window

        # Horizontal windows
        for r in range(board.rows):
            row_array = grid[r]
            for c in range(board.cols - 3):
                window = row_array[c : c + 4]
                score += evaluate_window(window)

        # Vertical windows
        for c in range(board.cols):
            col_array = [grid[r][c] for r in range(board.rows)]
            for r in range(board.rows - 3):
                window = col_array[r : r + 4]
                score += evaluate_window(window)

        # Positive diagonal
        for r in range(board.rows - 3):
            for c in range(board.cols - 3):
                window = [grid[r + i][c + i] for i in range(4)]
                score += evaluate_window(window)

        # Negative diagonal
        for r in range(3, board.rows):
            for c in range(board.cols - 3):
                window = [grid[r - i][c + i] for i in range(4)]
                score += evaluate_window(window)

        return score
