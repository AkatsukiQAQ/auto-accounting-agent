from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class BudgetPlan(Base):
    __tablename__ = "budget_plans"
    __table_args__ = (
        UniqueConstraint("period_type", "starts_on", "currency"),
        CheckConstraint("period_type IN ('week','month')", name="period_type"),
        CheckConstraint("status IN ('draft','active','closed')", name="status"),
        CheckConstraint("created_by IN ('user','agent','template')", name="created_by"),
        CheckConstraint("ends_on >= starts_on", name="dates"),
        CheckConstraint("planned_income_cents >= 0", name="income"),
        CheckConstraint("savings_target_cents >= 0", name="savings"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    period_type: Mapped[str] = mapped_column(String)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    planned_income_cents: Mapped[int | None] = mapped_column(BigInteger)
    savings_target_cents: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String, default="active", server_default="active")
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String, default="user", server_default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    items: Mapped[list["BudgetItem"]] = relationship(cascade="all, delete-orphan", order_by="BudgetItem.category_id")


class BudgetItem(Base):
    __tablename__ = "budget_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "category_id"),
        CheckConstraint("limit_cents >= 0", name="limit"),
        CheckConstraint("warning_ratio > 0 AND warning_ratio <= 1", name="warning_ratio"),
        CheckConstraint("kind IN ('fixed','flexible','discretionary')", name="kind"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("budget_plans.id", ondelete="CASCADE"))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    limit_cents: Mapped[int] = mapped_column(BigInteger)
    warning_ratio: Mapped[float] = mapped_column(Float, default=0.8, server_default="0.8")
    kind: Mapped[str] = mapped_column(String, default="flexible", server_default="flexible")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
