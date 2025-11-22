import argparse
import logging
from pathlib import Path

from .ai import MinimaxAI
from .board import Board, Player
from .config import GameConfig


def setup_logging(log_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="Play Connect Four against an AI opponent.")
    parser.add_argument("--depth", type=int, default=4, help="Search depth for AI (default: 4)")
    parser.add_argument("--human-first", action="store_true", help="Let the human play first")
    parser.add_argument("--log-file", type=Path, default=GameConfig().log_file, help="Path to log file")
    args = parser.parse_args()

    config = GameConfig(ai_depth=args.depth, log_file=args.log_file)
    config.log_config()
    setup_logging(config.log_file)

    board = Board()
    ai = MinimaxAI(depth=config.ai_depth)
    current_player = Player.HUMAN if args.human_first else Player.AI

    print("Starting Connect Four! Enter column numbers 0-6.")
    while True:
        print(board.render_ascii())
        over, winner = board.game_over()
        if over:
            if winner is None:
                print("It's a draw!")
            else:
                print(f"{winner.name} wins!")
            break

        if current_player == Player.HUMAN:
            try:
                col = int(input("Your move (0-6): "))
            except ValueError:
                print("Invalid input. Enter a number between 0 and 6.")
                continue
            if board.drop_piece(col, Player.HUMAN) is None:
                print("Invalid move. Try again.")
                continue
            current_player = Player.AI
        else:
            print("AI thinking...")
            move, diagnostics = ai.choose_move(board, Player.AI)
            board.drop_piece(move, Player.AI)
            logging.info(
                "AI move", extra={
                    "move": move,
                    "duration_s": diagnostics.duration_s,
                    "depth": diagnostics.search_depth,
                    "nodes": diagnostics.nodes_expanded,
                }
            )
            print(f"AI plays column {move} (searched {diagnostics.search_depth} levels in {diagnostics.duration_s:.3f}s)")
            current_player = Player.HUMAN


if __name__ == "__main__":
    run_cli()
