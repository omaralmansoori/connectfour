import logging
import tkinter as tk
from tkinter import messagebox

from .ai import MinimaxAI
from .board import Board, Player
from .config import GameConfig

logger = logging.getLogger(__name__)


class ConnectFourGUI:
    CELL_SIZE = 80
    PADDING = 10

    def __init__(self, config: GameConfig) -> None:
        self.config = config
        self.board = Board()
        self.ai = MinimaxAI(depth=config.ai_depth)
        self.game_over = False

        self.root = tk.Tk()
        self.root.title("Connect Four")

        self.status_var = tk.StringVar(value="Your turn")
        self.canvas = tk.Canvas(
            self.root,
            width=self.board.cols * self.CELL_SIZE + self.PADDING * 2,
            height=self.board.rows * self.CELL_SIZE + self.PADDING * 2,
            bg="white",
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        controls = tk.Frame(self.root)
        controls.pack(fill=tk.X)
        tk.Button(controls, text="New Game", command=self.reset).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(controls, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        self.draw_board()

    def reset(self) -> None:
        self.board.reset()
        self.game_over = False
        self.status_var.set("Your turn")
        self.draw_board()

    def handle_click(self, event: tk.Event) -> None:
        if self.game_over:
            messagebox.showinfo("Game over", "Reset to play again")
            return
        col = (event.x - self.PADDING) // self.CELL_SIZE
        if not self.board.is_valid_move(col):
            messagebox.showwarning("Invalid move", "Choose another column")
            return
        self.board.drop_piece(col, Player.HUMAN)
        self.draw_board()
        over, winner = self.board.game_over()
        if over:
            self.finish_game(winner)
            return
        self.status_var.set("AI thinking...")
        self.root.after(100, self.ai_move)

    def ai_move(self) -> None:
        move, diagnostics = self.ai.choose_move(self.board, Player.AI)
        self.board.drop_piece(move, Player.AI)
        logger.info(
            "GUI AI move", extra={
                "move": move,
                "duration_s": diagnostics.duration_s,
                "depth": diagnostics.search_depth,
                "nodes": diagnostics.nodes_expanded,
            }
        )
        self.draw_board()
        over, winner = self.board.game_over()
        if over:
            self.finish_game(winner)
        else:
            self.status_var.set("Your turn")

    def finish_game(self, winner: Player | None) -> None:
        self.game_over = True
        if winner is None:
            self.status_var.set("Draw!")
            messagebox.showinfo("Game over", "Draw!")
        else:
            self.status_var.set(f"{winner.name} wins!")
            messagebox.showinfo("Game over", f"{winner.name} wins!")

    def draw_board(self) -> None:
        self.canvas.delete("all")
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                x0 = self.PADDING + c * self.CELL_SIZE
                y0 = self.PADDING + r * self.CELL_SIZE
                x1 = x0 + self.CELL_SIZE
                y1 = y0 + self.CELL_SIZE
                self.canvas.create_rectangle(x0, y0, x1, y1, outline="black", fill="#0b61a4")
                token = self.board.grid[r][c]
                fill = "white"
                if token == int(Player.HUMAN):
                    fill = "red"
                elif token == int(Player.AI):
                    fill = "yellow"
                self.canvas.create_oval(
                    x0 + 5,
                    y0 + 5,
                    x1 - 5,
                    y1 - 5,
                    fill=fill,
                    outline="black",
                )

    def start(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(self.config.log_file), logging.StreamHandler()],
        )
        self.root.mainloop()


def launch_gui() -> None:
    config = GameConfig()
    config.log_config()
    app = ConnectFourGUI(config)
    app.start()


if __name__ == "__main__":
    launch_gui()
