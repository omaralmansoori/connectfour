from __future__ import annotations

from typing import List

from .board import MoveResult, Player


class TicTacToeBoard:
    rows: int = 3
    cols: int = 3

    def __init__(self) -> None:
        self.grid: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def clone(self) -> "TicTacToeBoard":
        new_board = TicTacToeBoard()
        new_board.grid = [row.copy() for row in self.grid]
        return new_board

    def reset(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = 0

    def is_valid_move(self, move: int) -> bool:
        row, col = divmod(move, self.cols)
        return 0 <= row < self.rows and 0 <= col < self.cols and self.grid[row][col] == 0

    def valid_moves(self) -> List[int]:
        return [idx for idx in range(self.rows * self.cols) if self.is_valid_move(idx)]

    def drop_piece(self, move: int, player: Player) -> Optional[MoveResult]:
        if not self.is_valid_move(move):
            return None
        row, col = divmod(move, self.cols)
        self.grid[row][col] = int(player)
        return MoveResult(row=row, col=col, player=player)

    def check_win(self, player: Player) -> bool:
        token = int(player)
        lines = []

        # Rows and columns
        lines.extend([[self.grid[r][c] for c in range(self.cols)] for r in range(self.rows)])
        lines.extend([[self.grid[r][c] for r in range(self.rows)] for c in range(self.cols)])

        # Diagonals
        lines.append([self.grid[i][i] for i in range(self.rows)])
        lines.append([self.grid[i][self.cols - 1 - i] for i in range(self.rows)])

        return any(all(cell == token for cell in line) for line in lines)

    def check_draw(self) -> bool:
        return all(cell != 0 for row in self.grid for cell in row)

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
        footer = " " + " ".join(str(i) for i in range(self.rows * self.cols))
        return "\n".join(lines + [footer])

    def is_empty(self) -> bool:
        return all(cell == 0 for row in self.grid for cell in row)


def evaluate_tictactoe(board: TicTacToeBoard, player: Player) -> int:
    """Return a heuristic score for the Tic-Tac-Toe position.

    The evaluator rewards immediate wins heavily, penalizes losses, and uses
    lightweight pattern scoring to keep the search informative at shallow
    depths. The numbers are intentionally small to keep the tree readable in
    the teaching UI.
    """

    game_over, winner = board.game_over()
    opponent = Player.AI if player == Player.HUMAN else Player.HUMAN

    if game_over:
        if winner is None:
            return 0
        return 50 if winner == player else -50

    score = 0

    def line_score(cells: List[int]) -> int:
        token = int(player)
        opp = int(opponent)
        if cells.count(token) == 2 and cells.count(0) == 1:
            return 10
        if cells.count(token) == 1 and cells.count(0) == 2:
            return 3
        if cells.count(opp) == 2 and cells.count(0) == 1:
            return -12
        return 0

    lines = []
    lines.extend([[board.grid[r][c] for c in range(board.cols)] for r in range(board.rows)])
    lines.extend([[board.grid[r][c] for r in range(board.rows)] for c in range(board.cols)])
    lines.append([board.grid[i][i] for i in range(board.rows)])
    lines.append([board.grid[i][board.cols - 1 - i] for i in range(board.rows)])

    for line in lines:
        score += line_score(line)

    # Prefer taking the center early; it's strategically strong in Tic-Tac-Toe
    if board.grid[1][1] == int(player):
        score += 4
    elif board.grid[1][1] == int(opponent):
        score -= 4

    return score
