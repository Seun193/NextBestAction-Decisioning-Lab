import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "customers.csv"
DB_PATH = ROOT / "data" / "nba_lab.db"
TABLE_NAME = "customers"


def infer_type(values):
    non_empty = [v.strip() for v in values if v is not None and v.strip() != ""]

    if not non_empty:
        return "TEXT"

    try:
        for value in non_empty:
            int(value)
        return "INTEGER"
    except ValueError:
        pass

    try:
        for value in non_empty:
            float(value)
        return "REAL"
    except ValueError:
        return "TEXT"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise RuntimeError("customers.csv contains no customer rows.")

    columns = reader.fieldnames
    if not columns:
        raise RuntimeError("customers.csv has no header.")

    column_types = {
        column: infer_type([row[column] for row in rows])
        for column in columns
    }

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(f'DROP TABLE IF EXISTS "{TABLE_NAME}"')

        definitions = []

        for column in columns:
            definition = f'"{column}" {column_types[column]}'

            if column == "customer_id":
                definition += " PRIMARY KEY"

            definitions.append(definition)

        create_sql = (
            f'CREATE TABLE "{TABLE_NAME}" ('
            + ", ".join(definitions)
            + ")"
        )

        cursor.execute(create_sql)

        placeholders = ", ".join("?" for _ in columns)
        quoted_columns = ", ".join(f'"{c}"' for c in columns)

        insert_sql = (
            f'INSERT INTO "{TABLE_NAME}" ({quoted_columns}) '
            f'VALUES ({placeholders})'
        )

        values = [
            tuple(row[column] if row[column] != "" else None for column in columns)
            for row in rows
        ]

        cursor.executemany(insert_sql, values)
        conn.commit()

        count = cursor.execute(
            f'SELECT COUNT(*) FROM "{TABLE_NAME}"'
        ).fetchone()[0]

    print("=" * 70)
    print("NBA DECISIONING LAB - CSV TO SQLITE LOADER")
    print("=" * 70)
    print(f"Source CSV : {CSV_PATH}")
    print(f"SQLite DB : {DB_PATH}")
    print(f"Table     : {TABLE_NAME}")
    print(f"Customers : {count:,}")
    print()
    print("Detected schema:")

    for column in columns:
        print(f"  {column:<30} {column_types[column]}")

    if count != len(rows):
        raise RuntimeError(
            f"Row-count mismatch: CSV={len(rows)}, SQLite={count}"
        )

    print()
    print("VALIDATION: PASS")


if __name__ == "__main__":
    main()
