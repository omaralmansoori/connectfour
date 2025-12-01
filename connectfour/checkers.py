from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .board import MoveResult, Player

Coordinate = Tuple[int, int]


@dataclass
class CheckersMove:
    path: List[Coordinate]
    captures: List[Coordinate]
    promotes: bool

    def as_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "captures": self.captures,
            "promotes": self.promotes,
        }


class CheckersBoard:
    rows: int = 8
    cols: int = 8

    # Pieces: 0 empty, 1 human man, 2 AI man, 3 human king, 4 AI king

    def __init__(self) -> None:
        self.grid: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.move_count = 0
        self.reset()

    def clone(self) -> "CheckersBoard":
        clone_board = CheckersBoard()
        clone_board.grid = [row.copy() for row in self.grid]
        clone_board.move_count = self.move_count
        return clone_board

    def reset(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = 0

        # AI starts at the top, Human at the bottom
        for r in range(3):
            for c in range(self.cols):
                if (r + c) % 2 == 1:
                    self.grid[r][c] = int(Player.AI)

        for r in range(self.rows - 3, self.rows):
            for c in range(self.cols):
                if (r + c) % 2 == 1:
                    self.grid[r][c] = int(Player.HUMAN)

        self.move_count = 0

    def _owner(self, piece: int) -> Optional[Player]:
        if piece in (1, 3):
            return Player.HUMAN
        if piece in (2, 4):
            return Player.AI
        return None

    def _is_king(self, piece: int) -> bool:
        return piece in (3, 4)

    def valid_moves(self, player: Player) -> List[CheckersMove]:  # type: ignore[override]
        capture_moves: List[CheckersMove] = []
        simple_moves: List[CheckersMove] = []

        for r in range(self.rows):
            for c in range(self.cols):
                piece = self.grid[r][c]
                if self._owner(piece) != player:
                    continue

                capture_moves.extend(self._capture_sequences(r, c, piece))
                simple_moves.extend(self._simple_moves(r, c, piece))

        # Captures are mandatory
        return capture_moves if capture_moves else simple_moves

    def _simple_moves(self, r: int, c: int, piece: int) -> List[CheckersMove]:
        moves: List[CheckersMove] = []
        directions = self._move_directions(piece)
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols and self.grid[nr][nc] == 0:
                promotes = self._will_promote(piece, nr)
                moves.append(CheckersMove(path=[(r, c), (nr, nc)], captures=[], promotes=promotes))
        return moves

    def _capture_sequences(self, r: int, c: int, piece: int) -> List[CheckersMove]:
        sequences: List[CheckersMove] = []
        directions = self._move_directions(piece)

        for dr, dc in directions:
            mid_r, mid_c = r + dr, c + dc
            land_r, land_c = r + 2 * dr, c + 2 * dc
            if not (0 <= land_r < self.rows and 0 <= land_c < self.cols):
                continue
            if not (0 <= mid_r < self.rows and 0 <= mid_c < self.cols):
                continue

            mid_piece = self.grid[mid_r][mid_c]
            if self._owner(mid_piece) is None or self._owner(mid_piece) == self._owner(piece):
                continue
            if self.grid[land_r][land_c] != 0:
                continue

            next_grid = [row.copy() for row in self.grid]
            next_grid[r][c] = 0
            next_grid[mid_r][mid_c] = 0
            next_piece = piece
            promotes_here = False
            if self._will_promote(piece, land_r):
                next_piece = self._promoted_piece(piece)
                promotes_here = True
            next_grid[land_r][land_c] = next_piece

            follow_sequences = self._capture_continuations(land_r, land_c, next_piece, next_grid)
            if follow_sequences:
                for seq in follow_sequences:
                    sequences.append(
                        CheckersMove(
                            path=[(r, c)] + seq.path,
                            captures=[(mid_r, mid_c)] + seq.captures,
                            promotes=promotes_here or seq.promotes,
                        )
                    )
            else:
                sequences.append(
                    CheckersMove(
                        path=[(r, c), (land_r, land_c)],
                        captures=[(mid_r, mid_c)],
                        promotes=promotes_here,
                    )
                )

        return sequences

    def _capture_continuations(
        self, r: int, c: int, piece: int, grid_state: List[List[int]]
    ) -> List[CheckersMove]:
        sequences: List[CheckersMove] = []
        directions = self._move_directions(piece)

        for dr, dc in directions:
            mid_r, mid_c = r + dr, c + dc
            land_r, land_c = r + 2 * dr, c + 2 * dc
            if not (0 <= land_r < self.rows and 0 <= land_c < self.cols):
                continue
            if not (0 <= mid_r < self.rows and 0 <= mid_c < self.cols):
                continue

            mid_piece = grid_state[mid_r][mid_c]
            if mid_piece == 0 or self._owner(mid_piece) == self._owner(piece):
                continue
            if grid_state[land_r][land_c] != 0:
                continue

            next_grid = [row.copy() for row in grid_state]
            next_grid[r][c] = 0
            next_grid[mid_r][mid_c] = 0
            next_piece = piece
            promotes_here = False
            if self._will_promote(piece, land_r):
                next_piece = self._promoted_piece(piece)
                promotes_here = True
            next_grid[land_r][land_c] = next_piece

            deeper = self._capture_continuations(land_r, land_c, next_piece, next_grid)
            if deeper:
                for seq in deeper:
                    sequences.append(
                        CheckersMove(
                            path=[(r, c)] + seq.path,
                            captures=[(mid_r, mid_c)] + seq.captures,
                            promotes=promotes_here or seq.promotes,
                        )
                    )
            else:
                sequences.append(
                    CheckersMove(
                        path=[(r, c), (land_r, land_c)],
                        captures=[(mid_r, mid_c)],
                        promotes=promotes_here,
                    )
                )

        return sequences

    def drop_piece(self, move: CheckersMove, player: Player) -> Optional[MoveResult]:
        if self._owner(self.grid[move.path[0][0]][move.path[0][1]]) != player:
            return None

        start_r, start_c = move.path[0]
        moving_piece = self.grid[start_r][start_c]
        self.grid[start_r][start_c] = 0

        for cap_r, cap_c in move.captures:
            self.grid[cap_r][cap_c] = 0

        end_r, end_c = move.path[-1]
        piece = moving_piece if self._is_king(moving_piece) else int(player)
        if move.promotes:
            piece = self._promoted_piece(piece)

        self.grid[end_r][end_c] = piece
        self.move_count += 1
        return MoveResult(row=end_r, col=end_c, player=player)

    def _will_promote(self, piece: int, row: int) -> bool:
        if self._is_king(piece):
            return False
        if piece == int(Player.HUMAN):
            return row == 0
        if piece == int(Player.AI):
            return row == self.rows - 1
        return False

    def _promoted_piece(self, piece: int) -> int:
        if piece in (1, 3):
            return 3
        if piece in (2, 4):
            return 4
        return piece

    def _move_directions(self, piece: int) -> List[Coordinate]:
        if self._is_king(piece):
            return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        if piece in (int(Player.HUMAN), 3):
            return [(-1, -1), (-1, 1)]
        if piece in (int(Player.AI), 4):
            return [(1, -1), (1, 1)]
        return []

    def check_win(self, player: Player) -> bool:
        opponent = Player.HUMAN if player == Player.AI else Player.AI
        opponent_pieces = any(self._owner(cell) == opponent for row in self.grid for cell in row)
        if not opponent_pieces:
            return True
        if not self.valid_moves(opponent):
            return True
        return False

    def check_draw(self) -> bool:
        # If neither player can move, declare a draw
        return not self.valid_moves(Player.HUMAN) and not self.valid_moves(Player.AI)

    def game_over(self) -> Tuple[bool, Optional[Player]]:
        if self.check_win(Player.HUMAN):
            return True, Player.HUMAN
        if self.check_win(Player.AI):
            return True, Player.AI
        if self.check_draw():
            return True, None
        return False, None

    def render_ascii(self) -> str:
        symbols = {
            0: ".",
            1: "h",
            2: "a",
            3: "H",
            4: "A",
        }
        lines = ["|" + " ".join(symbols[cell] for cell in row) + "|" for row in self.grid]
        footer = "  " + " ".join(str(c) for c in range(self.cols))
        return "\n".join(lines + [footer])

    def is_initial(self) -> bool:
        return self.move_count == 0


def evaluate_checkers(board: CheckersBoard, player: Player) -> int:
    opponent = Player.HUMAN if player == Player.AI else Player.AI

    def material_score(target: Player) -> int:
        score = 0
        for r in range(board.rows):
            for c in range(board.cols):
                piece = board.grid[r][c]
                if board._owner(piece) != target:
                    continue
                if board._is_king(piece):
                    score += 5
                else:
                    score += 3
                # Encourage advancement toward promotion
                if target == Player.HUMAN:
                    score += (board.rows - 1 - r) * 0.1
                else:
                    score += r * 0.1
        return score

    def mobility_score(target: Player) -> float:
        return len(board.valid_moves(target)) * 0.3

    def center_control(target: Player) -> float:
        center_rows = range(2, 6)
        center_cols = range(2, 6)
        return sum(
            0.25
            for r in center_rows
            for c in center_cols
            if board._owner(board.grid[r][c]) == target
        )

    if board.game_over()[0]:
        over, winner = board.game_over()
        if winner is None:
            return 0
        return 10_000 if winner == player else -10_000

    return int(
        (material_score(player) - material_score(opponent))
        + (mobility_score(player) - mobility_score(opponent))
        + (center_control(player) - center_control(opponent))
    )
