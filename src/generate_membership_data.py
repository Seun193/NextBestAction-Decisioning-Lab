import argparse
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"
OUTPUT_DIR = ROOT / "data" / "membership"

DEFAULT_SEED = 84
DEFAULT_AS_OF_DATE = date(2026, 9, 21)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic membership and subscription "
            "source data from existing NBA customers."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DB_PATH,
        help=f"SQLite database path. Default: {DB_PATH}",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory. Default: {OUTPUT_DIR}",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed. Default: {DEFAULT_SEED}",
    )

    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=DEFAULT_AS_OF_DATE,
        help=(
            "Reference date in YYYY-MM-DD format. "
            f"Default: {DEFAULT_AS_OF_DATE.isoformat()}"
        ),
    )

    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def load_customers(
    database_path: Path,
) -> list[dict]:
    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: {database_path}"
        )

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                customer_id,
                monthly_income,
                savings_balance,
                app_visits_30d,
                marketing_consent
            FROM customers
            ORDER BY customer_id
            """
        ).fetchall()

    if not rows:
        raise RuntimeError(
            "No customers found in the customers table."
        )

    return [dict(row) for row in rows]


def membership_probability(
    customer: dict,
) -> float:
    income_component = min(
        float(customer["monthly_income"]) / 20_000,
        0.20,
    )

    engagement_component = min(
        int(customer["app_visits_30d"]) / 100,
        0.20,
    )

    probability = (
        0.45
        + income_component
        + engagement_component
    )

    return min(max(probability, 0.35), 0.85)


def choose_membership_tier(
    customer: dict,
    rng: np.random.Generator,
) -> str:
    income = float(customer["monthly_income"])
    savings = float(customer["savings_balance"])
    app_visits = int(customer["app_visits_30d"])

    premium_score = (
        (income >= 5_500)
        + (savings >= 25_000)
        + (app_visits >= 12)
    )

    plus_score = (
        (income >= 3_000)
        + (savings >= 8_000)
        + (app_visits >= 6)
    )

    roll = rng.random()

    if premium_score >= 2:
        if roll < 0.50:
            return "PREMIUM"

        if roll < 0.85:
            return "PLUS"

        return "STANDARD"

    if plus_score >= 2:
        if roll < 0.55:
            return "PLUS"

        if roll < 0.70:
            return "PREMIUM"

        return "STANDARD"

    if roll < 0.75:
        return "STANDARD"

    if roll < 0.95:
        return "PLUS"

    return "PREMIUM"


def choose_membership_status(
    customer: dict,
    rng: np.random.Generator,
) -> str:
    app_visits = int(customer["app_visits_30d"])

    if app_visits >= 10:
        probabilities = [0.86, 0.05, 0.03, 0.06]
    elif app_visits >= 4:
        probabilities = [0.78, 0.08, 0.04, 0.10]
    else:
        probabilities = [0.64, 0.14, 0.05, 0.17]

    return str(
        rng.choice(
            [
                "ACTIVE",
                "INACTIVE",
                "SUSPENDED",
                "CANCELLED",
            ],
            p=probabilities,
        )
    )


def random_join_date(
    as_of_date: date,
    rng: np.random.Generator,
) -> date:
    days_back = int(
        rng.integers(
            0,
            (365 * 5) + 1,
        )
    )

    return (
        as_of_date
        - timedelta(
            days=days_back
        )
    )

def determine_end_date(
    join_date: date,
    membership_status: str,
    as_of_date: date,
    rng: np.random.Generator,
) -> date | None:
    if membership_status not in {
        "INACTIVE",
        "CANCELLED",
    }:
        return None

    if join_date >= as_of_date:
        return as_of_date

    available_days = (
        as_of_date - join_date
    ).days

    offset = int(
        rng.integers(
            1,
            available_days + 1,
        )
    )

    return (
        join_date
        + timedelta(
            days=offset
        )
    )


def parse_boolean_style(
    value,
    field_name: str,
) -> int:
    normalized = str(
        value
    ).strip().lower()

    mappings = {
        "0": 0,
        "1": 1,
        "false": 0,
        "true": 1,
    }

    if normalized not in mappings:
        raise ValueError(
            f"{field_name} must be "
            "0/1/true/false"
        )

    return mappings[
        normalized
    ]


def membership_consent(
    customer_consent,
    rng: np.random.Generator,
) -> int:
    """
    Preserve authoritative customer consent in most cases.

    A small deterministic proportion is deliberately mismatched
    so the data-quality layer has realistic reconciliation
    exceptions to detect.
    """
    consent = parse_boolean_style(
        customer_consent,
        "customer_marketing_consent",
    )

    if rng.random() < 0.015:
        return 1 - consent

    return consent


def build_members(
    customers: list[dict],
    as_of_date: date,
    rng: np.random.Generator,
) -> list[dict]:
    members = []

    for customer in customers:
        probability = membership_probability(
            customer
        )

        if rng.random() >= probability:
            continue

        member_number = len(members) + 1
        member_id = f"M{member_number:06d}"

        tier = choose_membership_tier(
            customer,
            rng,
        )

        status = choose_membership_status(
            customer,
            rng,
        )

        join_date = random_join_date(
            as_of_date,
            rng,
        )

        end_date = determine_end_date(
            join_date=join_date,
            membership_status=status,
            as_of_date=as_of_date,
            rng=rng,
        )

        created_at = (
            f"{join_date.isoformat()}T09:00:00"
        )

        updated_at = (
            f"{as_of_date.isoformat()}T12:00:00"
        )

        members.append(
            {
                "member_id": member_id,
                "customer_id": customer["customer_id"],
                "membership_status": status,
                "membership_tier": tier,
                "join_date": join_date.isoformat(),
                "end_date": (
                    end_date.isoformat()
                    if end_date
                    else ""
                ),
                "marketing_consent": (
                    membership_consent(
                        customer["marketing_consent"],
                        rng,
                    )
                ),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    return members


def plan_for_tier(
    tier: str,
) -> tuple[str, float]:
    plans = {
        "STANDARD": (
            "MEMBERSHIP_STANDARD",
            9.99,
        ),
        "PLUS": (
            "MEMBERSHIP_PLUS",
            19.99,
        ),
        "PREMIUM": (
            "MEMBERSHIP_PREMIUM",
            34.99,
        ),
    }

    return plans[tier]


def previous_plan_for_tier(
    tier: str,
) -> tuple[str, float] | None:
    if tier == "PREMIUM":
        return (
            "MEMBERSHIP_PLUS",
            19.99,
        )

    if tier == "PLUS":
        return (
            "MEMBERSHIP_STANDARD",
            9.99,
        )

    return None


def choose_renewal_status(
    membership_status: str,
    rng: np.random.Generator,
) -> str:
    if membership_status == "CANCELLED":
        return "CANCELLED"

    if membership_status == "INACTIVE":
        return "EXPIRED"

    if membership_status == "SUSPENDED":
        return str(
            rng.choice(
                ["DUE", "RENEWED"],
                p=[0.70, 0.30],
            )
        )

    return str(
        rng.choice(
            ["NEW", "RENEWED", "DUE"],
            p=[0.18, 0.62, 0.20],
        )
    )


def build_subscriptions(
    members: list[dict],
    as_of_date: date,
    rng: np.random.Generator,
) -> list[dict]:
    subscriptions = []
    subscription_number = 1

    for member in members:
        member_id = member["member_id"]
        tier = member["membership_tier"]
        status = member["membership_status"]

        join_date = date.fromisoformat(
            member["join_date"]
        )

        member_end_date = (
            date.fromisoformat(member["end_date"])
            if member["end_date"]
            else None
        )

        #
        # A membership lifecycle ends either at the explicit
        # membership end date or at the current as-of date.
        #
        # Subscription history must never extend beyond that
        # membership lifecycle.
        #
        lifecycle_end_date = (
            member_end_date
            if member_end_date is not None
            else as_of_date
        )

        membership_duration_days = (
            lifecycle_end_date - join_date
        ).days

        current_plan_name, current_price = (
            plan_for_tier(tier)
        )

        previous_plan = previous_plan_for_tier(
            tier
        )

        #
        # Historical plan transitions are only possible when
        # the membership itself lasted long enough.
        #
        create_history = (
            previous_plan is not None
            and membership_duration_days >= 365
            and rng.random() < 0.30
        )

        current_start_date = join_date

        if create_history:
            #
            # Permit plan transitions throughout the membership
            # lifecycle while keeping the transition before the
            # lifecycle end.
            #
            max_transition_day = (
                 membership_duration_days - 1
            )

            transition_days = int(
                rng.integers(
                    180,
                    max_transition_day + 1,
                )
            )

            transition_date = (
                join_date
                + timedelta(
                    days=transition_days
                )
            )

            previous_name, previous_price = (
                previous_plan
            )

            subscriptions.append(
                {
                    "subscription_id": (
                        f"S{subscription_number:07d}"
                    ),
                    "member_id": member_id,
                    "plan_name": previous_name,
                    "start_date": (
                        join_date.isoformat()
                    ),
                    "end_date": (
                        transition_date
                        - timedelta(days=1)
                    ).isoformat(),
                    "renewal_status": "RENEWED",
                    "auto_renew": 1,
                    "price": f"{previous_price:.2f}",
                    "currency": "EUR",
                    "billing_frequency": "MONTHLY",
                }
            )

            subscription_number += 1

            current_start_date = (
                transition_date
            )

        renewal_status = choose_renewal_status(
            status,
            rng,
        )

        auto_renew = (
            1
            if (
                status in {
                    "ACTIVE",
                    "SUSPENDED",
                }
                and rng.random() < 0.72
            )
            else 0
        )

        current_end_date = ""

        if status in {
            "INACTIVE",
            "CANCELLED",
        }:
            current_end_date = (
                lifecycle_end_date.isoformat()
            )

        subscriptions.append(
            {
                "subscription_id": (
                    f"S{subscription_number:07d}"
                ),
                "member_id": member_id,
                "plan_name": current_plan_name,
                "start_date": (
                    current_start_date.isoformat()
                ),
                "end_date": current_end_date,
                "renewal_status": renewal_status,
                "auto_renew": auto_renew,
                "price": f"{current_price:.2f}",
                "currency": "EUR",
                "billing_frequency": "MONTHLY",
            }
        )

        subscription_number += 1

    return subscriptions

def write_csv(
    path: Path,
    rows: list[dict],
) -> None:
    if not rows:
        raise RuntimeError(
            f"No rows generated for {path.name}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def count_by(
    rows: list[dict],
    field: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for row in rows:
        value = str(row[field])

        counts[value] = (
            counts.get(value, 0) + 1
        )

    return dict(
        sorted(
            counts.items(),
            key=lambda item: item[0],
        )
    )


def main() -> None:
    args = parse_args()

    database_path = resolve_path(
        args.database
    )

    output_dir = resolve_path(
        args.output_dir
    )

    customers = load_customers(
        database_path
    )

    rng = np.random.default_rng(
        args.seed
    )

    members = build_members(
        customers=customers,
        as_of_date=args.as_of_date,
        rng=rng,
    )

    subscriptions = build_subscriptions(
        members=members,
        as_of_date=args.as_of_date,
        rng=rng,
    )

    members_path = (
        output_dir / "members.csv"
    )

    subscriptions_path = (
        output_dir / "subscriptions.csv"
    )

    write_csv(
        members_path,
        members,
    )

    write_csv(
        subscriptions_path,
        subscriptions,
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "MEMBERSHIP SOURCE DATA GENERATOR"
    )
    print("=" * 70)

    print(
        f"Source customers : "
        f"{len(customers):,}"
    )

    print(
        f"Members generated: "
        f"{len(members):,}"
    )

    print(
        f"Subscriptions    : "
        f"{len(subscriptions):,}"
    )

    membership_rate = (
        len(members)
        / len(customers)
        * 100
    )

    print(
        f"Membership rate  : "
        f"{membership_rate:.2f}%"
    )

    print(
        f"Seed             : "
        f"{args.seed}"
    )

    print(
        f"As-of date       : "
        f"{args.as_of_date}"
    )

    print()

    print("Membership status distribution:")

    for value, count in count_by(
        members,
        "membership_status",
    ).items():
        print(
            f"  {value:<12} "
            f"{count:>8,}"
        )

    print()

    print("Membership tier distribution:")

    for value, count in count_by(
        members,
        "membership_tier",
    ).items():
        print(
            f"  {value:<12} "
            f"{count:>8,}"
        )

    print()

    print(
        f"Members file      : "
        f"{members_path}"
    )

    print(
        f"Subscriptions file: "
        f"{subscriptions_path}"
    )

    print()
    print("GENERATION: PASS")


if __name__ == "__main__":
    main()