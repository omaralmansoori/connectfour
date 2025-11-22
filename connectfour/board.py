from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Tuple


class Player(IntEnum):
    HUMAN = 1
    AI = 2


@dataclass
class MoveResult:
    row: int
    col: int
    player: Player


class Board:
    rows: int = 6
    cols: int = 7

    def __init__(self) -> None:
        self.grid: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def clone(self) -> "Board":
        new_board = Board()
        new_board.grid = [row.copy() for row in self.grid]
        return new_board

    def reset(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = 0

    def is_valid_move(self, col: int) -> bool:
        return 0 <= col < self.cols and self.grid[0][col] == 0

    def valid_moves(self) -> List[int]:
        return [c for c in range(self.cols) if self.is_valid_move(c)]

    def drop_piece(self, col: int, player: Player) -> Optional[MoveResult]:
        if not self.is_valid_move(col):
            return None
        for row in range(self.rows - 1, -1, -1):
            if self.grid[row][col] == 0:
                self.grid[row][col] = int(player)
                return MoveResult(row=row, col=col, player=player)
        return None

    def check_win(self, player: Player) -> bool:
        token = int(player)
        # Horizontal
        for r in range(self.rows):
            for c in range(self.cols - 3):
                if all(self.grid[r][c + i] == token for i in range(4)):
                    return True
        # Vertical
        for c in range(self.cols):
            for r in range(self.rows - 3):
                if all(self.grid[r + i][c] == token for i in range(4)):
                    return True
        # Positive diagonal
        for r in range(self.rows - 3):
            for c in range(self.cols - 3):
                if all(self.grid[r + i][c + i] == token for i in range(4)):
                    return True
        # Negative diagonal
        for r in range(3, self.rows):
            for c in range(self.cols - 3):
                if all(self.grid[r - i][c + i] == token for i in range(4)):
                    return True
        return False

    def check_draw(self) -> bool:
        return all(self.grid[0][c] != 0 for c in range(self.cols))

    def game_over(self) -> Tuple[bool, Optional[Player]]:
        for player in Player:
            if self.check_win(player):
                return True, player
        if self.check_draw():
            return True, None
        return False, None

    def render_ascii(self) -> str:
        symbols = {0: ".", int(Player.HUMAN): "X", int(Player.AI): "O"}
        lines = ["|" + " ".join(symbols[cell] for cell in row) + "|" for row in self.grid]
        footer = " " + " ".join(str(c) for c in range(self.cols))
        return "\n".join(lines + [footer])

    def __str__(self) -> str:  # pragma: no cover - helper
        return self.render_ascii()
