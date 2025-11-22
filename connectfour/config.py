from dataclasses import dataclass, field
from pathlib import Path


def default_log_file() -> Path:
    return Path.cwd() / "connectfour.log"


@dataclass
class GameConfig:
    ai_depth: int = 4
    log_file: Path = field(default_factory=default_log_file)

    def log_config(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
