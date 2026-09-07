"""
load_to_sqlite.py
---------------------------------
Loads the daily compliance drop CSV into a local SQLite database so the
RCA queries in ../sql/ are executed as real SQL against a real table,
not pandas operations dressed up as SQL.

Output: ../data/panel_ops.db  (table: compliance_drop)
"""

import sqlite3
import pandas as pd

CSV_PATH = "../data/compliance_drop_2026-09-01.csv"
DB_PATH = "../data/panel_ops.db"


def main():
    df = pd.read_csv(CSV_PATH)
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("compliance_drop", conn, if_exists="replace", index=False)

    # A couple of indexes -- worth mentioning in an interview as basic
    # pipeline hygiene, not just "it works."
    conn.execute("CREATE INDEX IF NOT EXISTS idx_market ON compliance_drop(market);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_device ON compliance_drop(device_type);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON compliance_drop(date);")
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM compliance_drop;").fetchone()[0]
    print(f"Loaded {count} rows into {DB_PATH}, table 'compliance_drop'.")
    conn.close()


if __name__ == "__main__":
    main()
