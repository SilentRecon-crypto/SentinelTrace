"""
scripts/seed_model_a.py

Imports the ALREADY-PERSISTED Stage 1 Model A dataset into PostgreSQL:

    data/model_a/accounts.csv
    data/model_a/transactions.csv
    data/model_a/complaints.csv

This script does NOT regenerate synthetic data. If these files are missing,
it fails loudly rather than falling back to generating a new world — the
canonical Stage 1 dataset (4,025 accounts / 38,830 transactions / 500
complaints) must come from disk, not be silently recreated.

Usage:
    python scripts/seed_model_a.py
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Account, Complaint, Transaction  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data" / "model_a"

EXPECTED_COLUMNS = {
    "accounts.csv": {"account_id", "acc_type", "created_day"},
    "transactions.csv": {"src", "dst", "day", "hour", "amount"},
    "complaints.csv": {"complaint_id", "victim", "day", "fraud_amount", "n_hops", "chain",
                        "used_shared_pool", "mode", "missing_hop_idx"},
}


class SeedError(RuntimeError):
    pass


def _load_and_validate(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise SeedError(
            f"Required Stage 1 data file not found: {path}\n"
            f"This script only imports already-persisted data. Run train_model_a.py "
            f"(Stage 1) first if this file is genuinely missing."
        )
    df = pd.read_csv(path)
    expected = EXPECTED_COLUMNS[filename]
    missing = expected - set(df.columns)
    if missing:
        raise SeedError(f"{filename} is missing expected columns: {missing}. Found columns: {list(df.columns)}")
    if len(df) == 0:
        raise SeedError(f"{filename} loaded but contains zero rows.")
    return df


def seed_accounts(df: pd.DataFrame) -> int:
    session = SessionLocal()
    try:
        rows = df[["account_id", "acc_type", "created_day"]].to_dict(orient="records")
        stmt = pg_insert(Account).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["account_id"],
            set_={"acc_type": stmt.excluded.acc_type, "created_day": stmt.excluded.created_day},
        )
        session.execute(stmt)
        session.commit()
        return len(rows)
    finally:
        session.close()


def seed_transactions(df: pd.DataFrame) -> int:
    session = SessionLocal()
    try:
        # Transactions have no natural unique key in the source data, and this
        # script is meant to be safely re-runnable, so we clear and reload
        # rather than trying to "upsert" rows with no stable identity.
        session.execute(text("TRUNCATE TABLE transactions RESTART IDENTITY"))
        rows = df.rename(columns={"src": "src_account_id", "dst": "dst_account_id"})[
            ["src_account_id", "dst_account_id", "day", "hour", "amount"]
        ].to_dict(orient="records")
        session.bulk_insert_mappings(Transaction, rows)
        session.commit()
        return len(rows)
    finally:
        session.close()


def seed_complaints(df: pd.DataFrame) -> int:
    session = SessionLocal()
    try:
        records = []
        for _, row in df.iterrows():
            chain = [int(x) for x in str(row["chain"]).split(",")]
            records.append(
                {
                    "complaint_id": int(row["complaint_id"]),
                    "victim": int(row["victim"]),
                    "day": int(row["day"]),
                    "fraud_amount": float(row["fraud_amount"]),
                    "n_hops": int(row["n_hops"]),
                    "chain": chain,
                    "used_shared_pool": bool(row["used_shared_pool"]),
                    "mode": str(row["mode"]),
                    "missing_hop_idx": int(row["missing_hop_idx"]),
                }
            )
        stmt = pg_insert(Complaint).values(records)
        update_cols = {c: stmt.excluded[c] for c in records[0] if c != "complaint_id"}
        stmt = stmt.on_conflict_do_update(index_elements=["complaint_id"], set_=update_cols)
        session.execute(stmt)
        session.commit()
        return len(records)
    finally:
        session.close()


def main():
    print("=" * 70)
    print("SentinelTrace Model A — database seed (Stage 2)")
    print("=" * 70)

    print("\n[1/4] Creating schema (if not already present)...")
    Base.metadata.create_all(bind=engine)
    print("    schema OK")

    print("\n[2/4] Loading and validating Stage 1 CSVs from disk...")
    accounts_df = _load_and_validate("accounts.csv")
    transactions_df = _load_and_validate("transactions.csv")
    complaints_df = _load_and_validate("complaints.csv")
    print(f"    accounts.csv: {len(accounts_df)} rows, columns OK")
    print(f"    transactions.csv: {len(transactions_df)} rows, columns OK")
    print(f"    complaints.csv: {len(complaints_df)} rows, columns OK")

    print("\n[3/4] Importing into PostgreSQL...")
    # Accounts first (transactions/complaints reference account_id via FK/logic).
    n_accounts = seed_accounts(accounts_df)
    print(f"    accounts upserted: {n_accounts}")
    n_transactions = seed_transactions(transactions_df)
    print(f"    transactions loaded (truncate+reload): {n_transactions}")
    n_complaints = seed_complaints(complaints_df)
    print(f"    complaints upserted: {n_complaints}")

    print("\n[4/4] Summary")
    print(f"    accounts     = {n_accounts}")
    print(f"    transactions = {n_transactions}")
    print(f"    complaints   = {n_complaints}")
    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except SeedError as exc:
        print(f"\nSEED FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
