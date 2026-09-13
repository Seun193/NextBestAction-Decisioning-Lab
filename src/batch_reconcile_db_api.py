import argparse
import csv
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from src.decision_engine import decide
from src.models import Customer
from src.repository import get_connection


DEFAULT_API_BASE = "http://127.0.0.1:8000"


def call_api(api_base: str, customer_id: str):
    url = f"{api_base}/nba/{customer_id}"

    try:
        with urlopen(url) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body

    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8")

        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = raw_body

        return exc.code, body

    except URLError as exc:
        raise RuntimeError(
            f"Cannot reach {api_base}. Start Uvicorn first."
        ) from exc


def normalize_ranked_actions(actions):
    return [
        {
            "action": item["action"],
            "score": item["score"],
            "eligible": item["eligible"],
            "reason_codes": item["reason_codes"],
        }
        for item in actions
    ]


def compare_response(expected, status, actual):
    mismatches = []

    checks = {
        "HTTP status": (200, status),
        "customer_id": (
            expected["customer_id"],
            actual.get("customer_id"),
        ),
        "next_best_action": (
            expected["next_best_action"],
            actual.get("next_best_action"),
        ),
        "score": (
            expected["score"],
            actual.get("score"),
        ),
        "eligible": (
            expected["eligible"],
            actual.get("eligible"),
        ),
        "reason_codes": (
            expected["reason_codes"],
            actual.get("reason_codes"),
        ),
        "ranked_actions": (
            normalize_ranked_actions(expected["ranked_actions"]),
            normalize_ranked_actions(
                actual.get("ranked_actions", [])
            ),
        ),
    }

    for field, (expected_value, actual_value) in checks.items():
        if expected_value != actual_value:
            mismatches.append(
                {
                    "field": field,
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )

    return mismatches


def load_customers(limit=None, offset=0):
    sql = """
        SELECT
            customer_id,
            age,
            monthly_income,
            savings_balance,
            monthly_surplus,
            has_mortgage,
            has_credit_card,
            investment_customer,
            app_visits_30d,
            marketing_consent,
            investment_consent,
            credit_score_band,
            preferred_channel
        FROM customers
        ORDER BY customer_id
    """

    params = []

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    elif offset:
        sql += " LIMIT -1 OFFSET ?"
        params.append(offset)

    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()

    return [Customer(**dict(row)) for row in rows]


def write_report(report_path, rows):
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "customer_id",
                "result",
                "field",
                "expected",
                "actual",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)


def run_batch(
    api_base,
    limit=None,
    offset=0,
    report_path=None,
    fail_fast=False,
):
    customers = load_customers(
        limit=limit,
        offset=offset,
    )

    print("=" * 90)
    print("NBA DATABASE -> API BATCH RECONCILIATION")
    print("=" * 90)
    print(f"API base       : {api_base}")
    print(f"Customers      : {len(customers):,}")
    print(f"Offset         : {offset:,}")
    print()

    if not customers:
        print("No customers selected.")
        return 0

    passed = 0
    failed = 0
    report_rows = []

    start_time = time.perf_counter()

    for index, customer in enumerate(customers, start=1):
        expected = decide(customer).model_dump()

        status, actual = call_api(
            api_base,
            customer.customer_id,
        )

        if status == 200 and isinstance(actual, dict):
            mismatches = compare_response(
                expected,
                status,
                actual,
            )
        else:
            mismatches = [
                {
                    "field": "HTTP status",
                    "expected": 200,
                    "actual": status,
                }
            ]

        if mismatches:
            failed += 1

            print(
                f"FAIL {customer.customer_id} "
                f"({len(mismatches)} mismatch(es))"
            )

            for mismatch in mismatches:
                print(
                    f"  {mismatch['field']}: "
                    f"expected={mismatch['expected']} "
                    f"actual={mismatch['actual']}"
                )

                report_rows.append(
                    {
                        "customer_id": customer.customer_id,
                        "result": "FAIL",
                        "field": mismatch["field"],
                        "expected": repr(
                            mismatch["expected"]
                        ),
                        "actual": repr(
                            mismatch["actual"]
                        ),
                    }
                )

            if fail_fast:
                break

        else:
            passed += 1

            report_rows.append(
                {
                    "customer_id": customer.customer_id,
                    "result": "PASS",
                    "field": "",
                    "expected": "",
                    "actual": "",
                }
            )

        if index % 100 == 0 or index == len(customers):
            print(
                f"Progress: {index:,}/{len(customers):,}"
            )

    elapsed = time.perf_counter() - start_time
    checked = passed + failed

    match_rate = (
        (passed / checked) * 100
        if checked
        else 0.0
    )

    throughput = (
        checked / elapsed
        if elapsed > 0
        else 0.0
    )

    print()
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"Customers checked : {checked:,}")
    print(f"Passed            : {passed:,}")
    print(f"Failed            : {failed:,}")
    print(f"Match rate        : {match_rate:.4f}%")
    print(f"Elapsed time      : {elapsed:.2f} seconds")
    print(f"Throughput        : {throughput:.2f} customers/second")

    if report_path:
        write_report(
            report_path,
            report_rows,
        )
        print(f"Report            : {report_path}")

    if failed:
        print("OVERALL: FAIL")
        return 1

    print("OVERALL: PASS")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Batch reconcile SQLite-driven NBA expectations "
            "with API responses."
        )
    )

    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=(
            "NBA API base URL. "
            f"Default: {DEFAULT_API_BASE}"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of customers to validate.",
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of ordered customers to skip.",
    )

    parser.add_argument(
        "--report",
        default=None,
        help="Optional CSV output path.",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed customer.",
    )

    args = parser.parse_args()

    exit_code = run_batch(
        api_base=args.api_base,
        limit=args.limit,
        offset=args.offset,
        report_path=args.report,
        fail_fast=args.fail_fast,
    )

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()