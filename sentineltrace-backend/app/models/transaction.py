"""
Transaction ORM model.

Source data (data/model_a/transactions.csv, from generate_graph_v1.py) has
columns: src, dst, day, hour, amount — and no natural unique identifier.

`transaction_id` below is DATABASE-GENERATED METADATA (a serial surrogate
key), not part of the source dataset. It exists only because a relational
table requires a primary key; it carries no research meaning. All other
columns are the source fields, renamed only where necessary for clarity
(src -> src_account_id, dst -> dst_account_id) while preserving their exact
values and semantics.
"""
from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    # DATABASE-GENERATED METADATA — not present in the source CSV.
    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Source fields (verbatim values from transactions.csv; src/dst renamed for clarity only)
    src_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False, index=True)
    dst_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False, index=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    src_account: Mapped["Account"] = relationship("Account", foreign_keys=[src_account_id], back_populates="outgoing_transactions")
    dst_account: Mapped["Account"] = relationship("Account", foreign_keys=[dst_account_id], back_populates="incoming_transactions")
