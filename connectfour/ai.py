from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

from .board import Board, Player

logger = logging.getLogger(__name__)


@dataclass
class MoveEvaluation:
    move: Any
    score: int


@dataclass
class SearchDiagnostics:
    evaluated_moves: List[MoveEvaluation]
    search_depth: int
    duration_s: float
    nodes_expanded: int
    search_tree: "SearchNode"
    principal_variation: List[Any]


@dataclass
class SearchNode:
    move: Any
    score: int
    depth: int
    maximizing: bool
    children: List["SearchNode"]


class MinimaxAI:
    def __init__(
        self, depth: int = 4, evaluator: Optional[Callable[[Any, Player], int]] = None
    ) -> None:
        self.depth = depth
        self._custom_evaluator = evaluator

    def choose_move(self, board: Board, player: Player = Player.AI) -> Tuple[Any, SearchDiagnostics]:
        start = time.perf_counter()
        evaluations: List[MoveEvaluation] = []
        nodes_expanded = 0

        def serialize_move(move: Any) -> Any:
            if hasattr(move, "as_dict"):
                return move.as_dict()  # type: ignore[no-any-return]
            return move

        def valid_moves(state: Board, current_player: Player) -> List[Any]:
            """Return valid moves for the given player, supporting boards that accept an argument.

            Connect Four/Tic-Tac-Toe ignore the player, while Checkers needs it for directional moves.
            """

            try:
                return state.valid_moves(current_player)  # type: ignore[arg-type]
            except TypeError:
                return state.valid_moves()

        def minimax(
            state: Board,
            depth: int,
            maximizing: bool,
            alpha: float,
            beta: float,
            move_from_parent: Optional[Any] = None,
        ) -> Tuple[int, Optional[Any], SearchNode]:
            nonlocal nodes_expanded
            nodes_expanded += 1
            game_over, winner = state.game_over()
            node = SearchNode(
                move=serialize_move(move_from_parent),
                score=0,
                depth=self.depth - depth,
                maximizing=maximizing,
                children=[],
            )
            if depth == 0 or game_over:
                eval_score = self._evaluate(state, player)
                node.score = eval_score
                return eval_score, None, node

            current_player = player if maximizing else Player.HUMAN if player == Player.AI else Player.AI
            valid = valid_moves(state, current_player)
            if maximizing:
                value = -float("inf")
                best_move: Optional[Any] = None
                for move in valid:
                    child = state.clone()
                    child.drop_piece(move, player)
                    score, _, child_node = minimax(
                        child, depth - 1, False, alpha, beta, move_from_parent=move
                    )
                    node.children.append(child_node)
                    if depth == self.depth:
                        evaluations.append(MoveEvaluation(move=serialize_move(move), score=score))
                    if score > value:
                        value = score
                        best_move = move
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break
                node.score = int(value)
                return int(value), best_move, node
            else:
                value = float("inf")
                best_move = None
                opp = Player.HUMAN if player == Player.AI else Player.AI
                for move in valid:
                    child = state.clone()
                    child.drop_piece(move, opp)
                    score, _, child_node = minimax(
                        child, depth - 1, True, alpha, beta, move_from_parent=move
                    )
                    node.children.append(child_node)
                    if score < value:
                        value = score
                        best_move = move
                    beta = min(beta, value)
                    if alpha >= beta:
                        break
                node.score = int(value)
                return int(value), best_move, node

        score, move, search_tree = minimax(
            board, self.depth, True, -float("inf"), float("inf"), move_from_parent=None
        )
        duration = time.perf_counter() - start
        if move is None:
            valid_moves = board.valid_moves()
            move = valid_moves[0] if valid_moves else -1

        def principal_variation(node: SearchNode) -> List[Any]:
            variation: List[Any] = []
            current = node
            while current.children:
                best_child: Optional[SearchNode] = None
                if current.maximizing:
                    best_score = max(child.score for child in current.children)
                    for child in current.children:
                        if child.score == best_score:
                            best_child = child
                            break
                else:
                    best_score = min(child.score for child in current.children)
                    for child in current.children:
                        if child.score == best_score:
                            best_child = child
                            break
                if best_child is None or best_child.move is None:
                    break
                variation.append(best_child.move)
                current = best_child
            return variation

        pv = principal_variation(search_tree)
        diagnostics = SearchDiagnostics(
            evaluated_moves=evaluations,
            search_depth=self.depth,
            duration_s=duration,
            nodes_expanded=nodes_expanded,
            search_tree=search_tree,
            principal_variation=pv,
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

    def _evaluate(self, board: Board, player: Player) -> int:
        if self._custom_evaluator:
            return self._custom_evaluator(board, player)
        return self.evaluate_board(board, player)

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
