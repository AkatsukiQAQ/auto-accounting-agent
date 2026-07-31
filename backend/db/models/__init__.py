"""Model registry. Importing this package registers every table on Base.metadata
— alembic's env.py and the test conftests rely on that side effect, so new
models only need to be added HERE (single registration point)."""
from backend.db.models.account import Account
from backend.db.models.category import Category
from backend.db.models.settings import UserSettings
from backend.db.models.transaction import Transaction

__all__ = ["Account", "Category", "Transaction", "UserSettings"]
