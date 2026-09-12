from .decision_engine import decide
from .models import Customer


def main() -> None:
    customer = Customer(
        customer_id="DEMO001",
        age=36,
        monthly_income=4500,
        savings_balance=18000,
        monthly_surplus=900,
        has_mortgage=False,
        has_credit_card=True,
        investment_customer=False,
        app_visits_30d=12,
        marketing_consent=True,
        investment_consent=True,
        credit_score_band="HIGH",
        preferred_channel="MOBILE",
    )

    result = decide(customer)

    print("\nCUSTOMER")
    print(customer.model_dump())

    print("\nNEXT BEST ACTION")
    print(f"{result.next_best_action}: {result.score:.2f}")

    print("\nRANKING")
    for item in result.ranked_actions:
        status = "ELIGIBLE" if item.eligible else "BLOCKED"
        print(
            f"{item.action:28s} "
            f"{item.score:.2f} "
            f"{status:8s} "
            f"{', '.join(item.reason_codes)}"
        )


if __name__ == "__main__":
    main()
