import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from src.repository import get_customer
from src.decision_engine import decide


API_BASE = "http://127.0.0.1:8000"


def call_api(customer_id: str):
    url = f"{API_BASE}/nba/{customer_id}"

    try:
        with urlopen(url) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body

    except HTTPError as exc:
        body = exc.read().decode("utf-8")

        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass

        return exc.code, body

    except URLError as exc:
        raise RuntimeError(
            f"Cannot reach {API_BASE}. Start Uvicorn first."
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


def compare(name, expected, actual):
    passed = expected == actual

    print(
        f"{name:<24} "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        print(f"  Expected: {expected}")
        print(f"  Actual  : {actual}")

    return passed


def reconcile(customer_id: str):
    print()
    print("=" * 90)
    print(f"NBA DATABASE -> API RECONCILIATION: {customer_id}")
    print("=" * 90)

    customer = get_customer(customer_id)

    print("\n1. DATABASE LOOKUP")
    print("-" * 90)

    if customer is None:
        print("Customer not found in SQLite.")

        status, body = call_api(customer_id)

        print("\n2. API LOOKUP")
        print("-" * 90)
        print(f"HTTP status: {status}")

        print("\n3. VALIDATION")
        print("-" * 90)

        if status == 404:
            print("OVERALL: PASS")
            print("Database customer absent and API correctly returned 404.")
        else:
            print("OVERALL: FAIL")
            print(
                f"Database customer absent but API returned HTTP {status}."
            )

        return

    print(f"customer_id              : {customer.customer_id}")
    print(f"age                      : {customer.age}")
    print(f"monthly_income           : {customer.monthly_income}")
    print(f"savings_balance          : {customer.savings_balance}")
    print(f"monthly_surplus          : {customer.monthly_surplus}")
    print(f"has_mortgage             : {customer.has_mortgage}")
    print(f"has_credit_card          : {customer.has_credit_card}")
    print(f"investment_customer      : {customer.investment_customer}")
    print(f"app_visits_30d           : {customer.app_visits_30d}")
    print(f"marketing_consent        : {customer.marketing_consent}")
    print(f"investment_consent       : {customer.investment_consent}")
    print(f"credit_score_band        : {customer.credit_score_band}")
    print(f"preferred_channel        : {customer.preferred_channel}")

    expected = decide(customer).model_dump()

    print("\n2. EXPECTED DECISION FROM DATABASE INPUT")
    print("-" * 90)
    print(f"next_best_action         : {expected['next_best_action']}")
    print(f"score                    : {expected['score']}")
    print(f"eligible                 : {expected['eligible']}")
    print(
        "reason_codes             : "
        + ", ".join(expected["reason_codes"])
    )

    status, actual = call_api(customer_id)

    print("\n3. ACTUAL API DECISION")
    print("-" * 90)
    print(f"HTTP status              : {status}")

    if status != 200:
        print(actual)
        print("\nOVERALL: FAIL")
        return

    print(f"next_best_action         : {actual['next_best_action']}")
    print(f"score                    : {actual['score']}")
    print(f"eligible                 : {actual['eligible']}")
    print(
        "reason_codes             : "
        + ", ".join(actual["reason_codes"])
    )

    print("\n4. RECONCILIATION")
    print("-" * 90)

    results = [
        compare(
            "HTTP status",
            200,
            status,
        ),
        compare(
            "customer_id",
            expected["customer_id"],
            actual["customer_id"],
        ),
        compare(
            "next_best_action",
            expected["next_best_action"],
            actual["next_best_action"],
        ),
        compare(
            "score",
            expected["score"],
            actual["score"],
        ),
        compare(
            "eligible",
            expected["eligible"],
            actual["eligible"],
        ),
        compare(
            "reason_codes",
            expected["reason_codes"],
            actual["reason_codes"],
        ),
        compare(
            "ranked_actions",
            normalize_ranked_actions(expected["ranked_actions"]),
            normalize_ranked_actions(actual["ranked_actions"]),
        ),
    ]

    print("\n5. RESULT")
    print("-" * 90)

    if all(results):
        print("OVERALL: PASS")
        print(
            "SQLite customer data produced the same NBA decision "
            "through the API."
        )
    else:
        print("OVERALL: FAIL")
        print("One or more reconciliation checks failed.")


def main():
    parser = argparse.ArgumentParser(
        description="Reconcile SQLite-driven NBA expectations with API output."
    )

    parser.add_argument(
        "customer_ids",
        nargs="+",
        help="Customer IDs, e.g. C00001 C00002 C00003",
    )

    args = parser.parse_args()

    for customer_id in args.customer_ids:
        reconcile(customer_id)


if __name__ == "__main__":
    main()
