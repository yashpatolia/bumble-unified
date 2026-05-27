from pathlib import Path
from .manager import DatabaseManager

manager = DatabaseManager(str(Path(__file__).parent.parent.parent / "bumble.db"))
