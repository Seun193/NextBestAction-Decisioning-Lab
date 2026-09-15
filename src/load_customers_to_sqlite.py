import argparse
import csv
import sqlite3
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "customers.csv"
DB_PATH = ROOT / "data" / "nba_lab.db"
TABLE_NAME = "customers"
DEFAULT_BATCH_SIZE = 10_000


def value_type(value: str) -> str | None:
    value = value.strip()

    if value == "":
        return None

    try:
        int(value)
        return "INTEGER"
    except ValueError:
        pass

    try:
        float(value)
        return "REAL"
    except ValueError:
        return "TEXT"


def merge_types(current: str | None, new: str | None) -> str | None:
    if new is None:
        return current

    if current is None:
        return new

    if current == "TEXT" or new == "TEXT":
        return "TEXT"

    if current == "REAL" or new == "REAL":
        return "REAL"

    return "INTEGER"


def inspect_csv(csv_path: Path) -> tuple[list[str], dict[str, str], int]:
    """
    First streaming pass.

    Determines:
    - CSV columns
    - SQLite-compatible column types
    - source row count

    No complete copy of the CSV is kept in memory.
    """
    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)

        columns = reader.fieldnames

        if not columns:
            raise RuntimeError("customers.csv has no header.")

        detected_types: dict[str, str | None] = {
            column: None
            for column in columns
        }

        row_count = 0

        for row in reader:
            row_count += 1

            for column in columns:
                detected_types[column] = merge_types(
                    detected_types[column],
                    value_type(row[column]),
                )

    if row_count == 0:
        raise RuntimeError("customers.csv contains no customer rows.")

    column_types = {
        column: detected_types[column] or "TEXT"
        for column in columns
    }

    return columns, column_types, row_count


def insert_csv_in_batches(
    conn: sqlite3.Connection,
    csv_path: Path,
    columns: list[str],
    batch_size: int,
) -> int:
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)

    insert_sql = (
        f'INSERT INTO "{TABLE_NAME}" ({quoted_columns}) '
        f"VALUES ({placeholders})"
    )

    inserted = 0
    batch: list[tuple] = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            values = tuple(
                row[column] if row[column] != "" else None
                for column in columns
            )

            batch.append(values)

            if len(batch) >= batch_size:
                conn.executemany(insert_sql, batch)
                inserted += len(batch)
                batch.clear()

        if batch:
            conn.executemany(insert_sql, batch)
            inserted += len(batch)

    return inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load NBA customer CSV data into SQLite."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=CSV_PATH,
        help=f"Input CSV path. Default: {CSV_PATH}",
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DB_PATH,
        help=f"SQLite database path. Default: {DB_PATH}",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Rows inserted per SQLite batch. "
            f"Default: {DEFAULT_BATCH_SIZE:,}"
        ),
    )

    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def main() -> None:
    args = parse_args()

    csv_path = resolve_path(args.input)
    db_path = resolve_path(args.database)

    if args.batch_size < 1:
        raise ValueError("Batch size must be at least 1.")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    total_start = perf_counter()

    inspect_start = perf_counter()

    columns, column_types, source_count = inspect_csv(csv_path)

    inspect_seconds = perf_counter() - inspect_start

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    load_start = perf_counter()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            f'DROP TABLE IF EXISTS "{TABLE_NAME}"'
        )

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

        inserted = insert_csv_in_batches(
            conn=conn,
            csv_path=csv_path,
            columns=columns,
            batch_size=args.batch_size,
        )

        conn.commit()

        database_count = cursor.execute(
            f'SELECT COUNT(*) FROM "{TABLE_NAME}"'
        ).fetchone()[0]

    load_seconds = perf_counter() - load_start
    total_seconds = perf_counter() - total_start

    print("=" * 70)
    print("NBA DECISIONING LAB - CSV TO SQLITE LOADER")
    print("=" * 70)
    print(f"Source CSV     : {csv_path}")
    print(f"SQLite DB     : {db_path}")
    print(f"Table         : {TABLE_NAME}")
    print(f"Source rows   : {source_count:,}")
    print(f"Inserted rows : {inserted:,}")
    print(f"Database rows : {database_count:,}")
    print(f"Batch size    : {args.batch_size:,}")
    print()
    print("Detected schema:")

    for column in columns:
        print(
            f"  {column:<30} "
            f"{column_types[column]}"
        )

    if inserted != source_count:
        raise RuntimeError(
            "Insert-count mismatch: "
            f"CSV={source_count:,}, inserted={inserted:,}"
        )

    if database_count != source_count:
        raise RuntimeError(
            "Row-count mismatch: "
            f"CSV={source_count:,}, SQLite={database_count:,}"
        )

    print()
    print("Performance:")
    print(f"  CSV inspection : {inspect_seconds:.3f} seconds")
    print(f"  SQLite load    : {load_seconds:.3f} seconds")
    print(f"  Total elapsed  : {total_seconds:.3f} seconds")

    if load_seconds > 0:
        throughput = database_count / load_seconds
        print(
            f"  Load throughput: {throughput:,.2f} rows/second"
        )

    print()
    print("VALIDATION: PASS")


if __name__ == "__main__":
    main()