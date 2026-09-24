"""Model registry. Importing this package registers every table on Base.metadata
— alembic's env.py and the test conftests rely on that side effect, so new
models only need to be added HERE (single registration point)."""
from backend.db.models.account import Account
from backend.db.models.budget import BudgetPlan, BudgetItem
from backend.db.models.category import Category
from backend.db.models.chat import ChatSession, ChatMessage, AgentAction
from backend.db.models.merchant import Merchant, MerchantAlias
from backend.db.models.settings import UserSettings
from backend.db.models.transaction import Transaction

__all__ = ["BudgetPlan", "BudgetItem", "Account", "Category", "Merchant", "MerchantAlias", "Transaction", "UserSettings",
           "ChatSession", "ChatMessage", "AgentAction"]
