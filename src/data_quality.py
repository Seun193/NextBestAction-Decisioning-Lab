import argparse
import csv
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "data" / "customers.csv"
DB_FILE = ROOT / "data" / "nba_lab.db"

REQUIRED_FIELDS = [
    "customer_id",
    "age",
    "monthly_income",
    "savings_balance",
    "monthly_surplus",
    "has_mortgage",
    "has_credit_card",
    "investment_customer",
    "app_visits_30d",
    "marketing_consent",
    "investment_consent",
    "credit_score_band",
    "preferred_channel",
]

BOOLEAN_FIELDS = [
    "has_mortgage",
    "has_credit_card",
    "investment_customer",
    "marketing_consent",
    "investment_consent",
]

VALID_CREDIT_BANDS = {"LOW", "MEDIUM", "HIGH"}
VALID_CHANNELS = {"MOBILE", "WEB", "BRANCH", "PHONE"}

CUSTOMER_ID_PATTERN = re.compile(r"^C\d{5}$")


def is_missing(value):
    return value is None or (
        isinstance(value, str) and value.strip() == ""
    )


def as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_integer_value(value):
    number = as_number(value)

    if number is None:
        return False

    return number.is_integer()


def is_valid_boolean(value):
    if isinstance(value, bool):
        return True

    if isinstance(value, int) and value in {0, 1}:
        return True

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "false",
            "0",
            "1",
        }

    return False


def add_error(errors, code, row, field, value, message):
    errors.append(
        {
            "code": code,
            "row": row,
            "field": field,
            "value": value,
            "message": message,
        }
    )


def validate_records(records):
    errors = []
    seen_customer_ids = set()

    for row_number, record in enumerate(records, start=1):

        # DQ-001
        for field in REQUIRED_FIELDS:
            if field not in record or is_missing(record.get(field)):
                add_error(
                    errors,
                    "DQ-001",
                    row_number,
                    field,
                    record.get(field),
                    "Required field is missing or empty",
                )

        customer_id = record.get("customer_id")

        if not is_missing(customer_id):

            # DQ-002
            if not CUSTOMER_ID_PATTERN.fullmatch(str(customer_id)):
                add_error(
                    errors,
                    "DQ-002",
                    row_number,
                    "customer_id",
                    customer_id,
                    "Invalid customer ID format",
                )

            # DQ-003
            if customer_id in seen_customer_ids:
                add_error(
                    errors,
                    "DQ-003",
                    row_number,
                    "customer_id",
                    customer_id,
                    "Duplicate customer ID",
                )

            seen_customer_ids.add(customer_id)

        # DQ-004
        age = record.get("age")

        if not is_missing(age):
            if (
                not is_integer_value(age)
                or not 18 <= float(age) <= 75
            ):
                add_error(
                    errors,
                    "DQ-004",
                    row_number,
                    "age",
                    age,
                    "Age must be an integer between 18 and 75",
                )

        # DQ-005
        monthly_income = as_number(record.get("monthly_income"))

        if (
            not is_missing(record.get("monthly_income"))
            and (
                monthly_income is None
                or not 900 <= monthly_income <= 14000
            )
        ):
            add_error(
                errors,
                "DQ-005",
                row_number,
                "monthly_income",
                record.get("monthly_income"),
                "Monthly income outside allowed range",
            )

        # DQ-006
        savings_balance = as_number(record.get("savings_balance"))

        if (
            not is_missing(record.get("savings_balance"))
            and (
                savings_balance is None
                or not 0 <= savings_balance <= 250000
            )
        ):
            add_error(
                errors,
                "DQ-006",
                row_number,
                "savings_balance",
                record.get("savings_balance"),
                "Savings balance outside allowed range",
            )

        # DQ-007
        monthly_surplus = as_number(record.get("monthly_surplus"))

        if (
            not is_missing(record.get("monthly_surplus"))
            and (
                monthly_surplus is None
                or not -1500 <= monthly_surplus <= 5000
            )
        ):
            add_error(
                errors,
                "DQ-007",
                row_number,
                "monthly_surplus",
                record.get("monthly_surplus"),
                "Monthly surplus outside allowed range",
            )

        # DQ-008
        app_visits = record.get("app_visits_30d")

        if not is_missing(app_visits):
            if (
                not is_integer_value(app_visits)
                or not 0 <= float(app_visits) <= 50
            ):
                add_error(
                    errors,
                    "DQ-008",
                    row_number,
                    "app_visits_30d",
                    app_visits,
                    "App visits must be an integer between 0 and 50",
                )

        # DQ-009
        for field in BOOLEAN_FIELDS:
            value = record.get(field)

            if (
                not is_missing(value)
                and not is_valid_boolean(value)
            ):
                add_error(
                    errors,
                    "DQ-009",
                    row_number,
                    field,
                    value,
                    "Invalid boolean value",
                )

        # DQ-010
        credit_band = record.get("credit_score_band")

        if (
            not is_missing(credit_band)
            and credit_band not in VALID_CREDIT_BANDS
        ):
            add_error(
                errors,
                "DQ-010",
                row_number,
                "credit_score_band",
                credit_band,
                "Invalid credit score band",
            )

        # DQ-011
        channel = record.get("preferred_channel")

        if (
            not is_missing(channel)
            and channel not in VALID_CHANNELS
        ):
            add_error(
                errors,
                "DQ-011",
                row_number,
                "preferred_channel",
                channel,
                "Invalid preferred channel",
            )

    return errors


def read_csv_records():
    with CSV_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


def read_sqlite_records():
    with sqlite3.connect(DB_FILE) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            "SELECT * FROM customers"
        ).fetchall()

    return [dict(row) for row in rows]


def main():
    parser = argparse.ArgumentParser(
        description="Validate NBA customer data quality."
    )

    parser.add_argument(
        "--source",
        choices=["csv", "sqlite"],
        default="sqlite",
    )

    args = parser.parse_args()

    records = (
        read_csv_records()
        if args.source == "csv"
        else read_sqlite_records()
    )

    errors = validate_records(records)

    print("=" * 70)
    print("NBA DATA QUALITY VALIDATION")
    print("=" * 70)
    print(f"Source       : {args.source}")
    print(f"Rows checked : {len(records):,}")
    print(f"Errors       : {len(errors):,}")

    if errors:
        print("\nFirst errors:")

        for error in errors[:20]:
            print(
                f"{error['code']} "
                f"row={error['row']} "
                f"field={error['field']} "
                f"value={error['value']!r} "
                f"- {error['message']}"
            )

        print("\nVALIDATION: FAIL")
        raise SystemExit(1)

    print("\nVALIDATION: PASS")


if __name__ == "__main__":
    main()