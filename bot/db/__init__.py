import os
from .manager import DatabaseManager

_DSN = os.getenv("DATABASE_URL", "")
manager = DatabaseManager(_DSN)
