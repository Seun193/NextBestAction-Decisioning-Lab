import argparse
import csv
import random
import sqlite3
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"

OUTPUT_PATH = (
    ROOT
    / "data"
    / "membership"
    / "benefit_redemptions.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)
DEFAULT_SEED = 168

LOOKBACK_DAYS = 180
POST_ELIGIBILITY_ATTEMPT_DAYS = 30


BENEFITS = {
    "WELCOME_REWARD": {
        "value": 5.00,
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
    },
    "PARTNER_DISCOUNT": {
        "value": 8.00,
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
    },
    "DIGITAL_REWARD": {
        "value": 4.00,
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
    },
    "DINING_CREDIT": {
        "value": 12.00,
        "tiers": {
            "PLUS",
            "PREMIUM",
        },
    },
    "EVENT_DISCOUNT": {
        "value": 15.00,
        "tiers": {
            "PLUS",
            "PREMIUM",
        },
    },
    "PREMIUM_EVENT": {
        "value": 30.00,
        "tiers": {
            "PREMIUM",
        },
    },
}


TIER_ACTIVITY_BONUS = {
    "STANDARD": 0,
    "PLUS": 1,
    "PREMIUM": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic synthetic "
            "membership benefit redemptions."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DB_PATH,
        help=f"SQLite database. Default: {DB_PATH}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output CSV. Default: {OUTPUT_PATH}",
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

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=(
            "Random seed for deterministic generation. "
            f"Default: {DEFAULT_SEED}"
        ),
    )

    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def load_members(
    connection: sqlite3.Connection,
) -> list[dict]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            member_id,
            membership_status,
            membership_tier,
            join_date,
            end_date
        FROM members
        ORDER BY member_id
        """
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def load_suspension_dates(
    connection: sqlite3.Connection,
) -> dict[str, date]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            member_id,
            MAX(event_timestamp)
                AS event_timestamp
        FROM membership_events
        WHERE event_type = 'SUSPENDED'
        GROUP BY member_id
        """
    ).fetchall()

    result = {}

    for row in rows:
        raw_timestamp = row[
            "event_timestamp"
        ]

        if not raw_timestamp:
            continue

        result[
            row["member_id"]
        ] = datetime.fromisoformat(
            raw_timestamp
        ).date()

    return result

def load_tier_history(
    connection: sqlite3.Connection,
) -> dict[str, list[tuple[date, str]]]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            member_id,
            event_type,
            event_timestamp,
            new_tier
        FROM membership_events
        WHERE event_type IN (
            'JOINED',
            'UPGRADED',
            'DOWNGRADED'
        )
        ORDER BY
            member_id,
            event_timestamp,
            event_id
        """
    ).fetchall()

    history: dict[
        str,
        list[tuple[date, str]],
    ] = {}

    for row in rows:
        new_tier = row["new_tier"]

        if not new_tier:
            continue

        effective_date = (
            datetime.fromisoformat(
                row["event_timestamp"]
            ).date()
        )

        history.setdefault(
            row["member_id"],
            [],
        ).append(
            (
                effective_date,
                new_tier,
            )
        )

    return history


def eligibility_end_date(
    member: dict,
    suspension_dates: dict[str, date],
    as_of_date: date,
) -> date:
    status = member[
        "membership_status"
    ]

    if status in {
        "INACTIVE",
        "CANCELLED",
    }:
        if not member["end_date"]:
            raise ValueError(
                f"{member['member_id']}: "
                f"{status} member has no end_date"
            )

        return min(
            date.fromisoformat(
                member["end_date"]
            ),
            as_of_date,
        )

    if status == "SUSPENDED":
        suspension_date = (
            suspension_dates.get(
                member["member_id"]
            )
        )

        if not suspension_date:
            raise ValueError(
                f"{member['member_id']}: "
                "SUSPENDED member has no "
                "suspension event"
            )

        return min(
            suspension_date,
            as_of_date,
        )

    if status == "ACTIVE":
        return as_of_date

    raise ValueError(
        f"Unsupported membership status: "
        f"{status}"
    )


def redemption_attempt_window(
    member: dict,
    suspension_dates: dict[str, date],
    as_of_date: date,
) -> tuple[date, date, date]:
    join_date = date.fromisoformat(
        member["join_date"]
    )

    eligible_until = (
        eligibility_end_date(
            member=member,
            suspension_dates=(
                suspension_dates
            ),
            as_of_date=as_of_date,
        )
    )

    if (
        member["membership_status"]
        == "ACTIVE"
    ):
        attempt_end = as_of_date
    else:
        attempt_end = min(
            as_of_date,
            eligible_until
            + timedelta(
                days=(
                    POST_ELIGIBILITY_ATTEMPT_DAYS
                )
            ),
        )

    attempt_start = max(
        join_date,
        attempt_end
        - timedelta(
            days=LOOKBACK_DAYS
        ),
    )

    return (
        attempt_start,
        attempt_end,
        eligible_until,
    )


def redemption_count(
    member: dict,
    rng: random.Random,
) -> int:
    status = member[
        "membership_status"
    ]

    tier = member[
        "membership_tier"
    ]

    tier_bonus = (
        TIER_ACTIVITY_BONUS[tier]
    )

    if status == "ACTIVE":
        return (
            rng.randint(
                1,
                3,
            )
            + tier_bonus
        )

    if status == "SUSPENDED":
        return rng.randint(
            0,
            2,
        )

    if status == "INACTIVE":
        return rng.randint(
            0,
            2,
        )

    if status == "CANCELLED":
        return rng.randint(
            0,
            2,
        )

    raise ValueError(
        f"Unsupported membership status: "
        f"{status}"
    )


def benefits_for_tier(
    tier: str,
) -> list[str]:
    return [
        benefit_code
        for benefit_code, definition
        in BENEFITS.items()
        if tier in definition["tiers"]
    ]

def tier_on_date(
    member_id: str,
    target_date: date,
    tier_history: dict[
        str,
        list[tuple[date, str]],
    ],
) -> str:
    history = tier_history.get(
        member_id,
        [],
    )

    current_tier = None

    for effective_date, new_tier in history:
        if effective_date > target_date:
            break

        current_tier = new_tier

    if current_tier is None:
        raise ValueError(
            f"{member_id}: no membership tier "
            f"found for {target_date}"
        )

    return current_tier


def random_timestamp(
    start_date: date,
    end_date: date,
    rng: random.Random,
) -> datetime:
    available_days = (
        end_date
        - start_date
    ).days

    day_offset = rng.randint(
        0,
        available_days,
    )

    event_date = (
        start_date
        + timedelta(
            days=day_offset
        )
    )

    event_time = time(
        hour=rng.randint(
            8,
            21,
        ),
        minute=rng.randint(
            0,
            59,
        ),
        second=rng.randint(
            0,
            59,
        ),
    )

    return datetime.combine(
        event_date,
        event_time,
    )


def choose_status(
    redemption_date: date,
    eligible_until: date,
    rng: random.Random,
) -> str:
    #
    # Once eligibility has ended, attempts may
    # still reach the system but must fail.
    #
    if redemption_date > eligible_until:
        return "FAILED"

    roll = rng.random()

    if roll < 0.78:
        return "REDEEMED"

    if roll < 0.88:
        return "REVERSED"

    return "FAILED"


def monetary_value(
    benefit_code: str,
    redemption_status: str,
) -> str:
    if redemption_status == "FAILED":
        return ""

    value = BENEFITS[
        benefit_code
    ]["value"]

    return f"{value:.2f}"


def build_benefit_redemptions(
    members: list[dict],
    suspension_dates: dict[str, date],
    tier_history: dict[
        str,
        list[tuple[date, str]],
    ],
    as_of_date: date,
    seed: int,
) -> list[dict]:
    rng = random.Random(
        seed
    )

    rows = []

    for member in members:
        (
            attempt_start,
            attempt_end,
            eligible_until,
        ) = redemption_attempt_window(
            member=member,
            suspension_dates=(
                suspension_dates
            ),
            as_of_date=as_of_date,
        )

        if attempt_end < attempt_start:
            raise ValueError(
                f"{member['member_id']}: "
                "invalid redemption attempt window"
            )

        count = redemption_count(
            member,
            rng,
        )

        for _ in range(
            count
        ):
            #
            # Generate the event time first.
            #
            # Benefit eligibility must be evaluated
            # using the tier the member actually held
            # on that historical date, not today's tier.
            #
            redemption_timestamp = (
                random_timestamp(
                    start_date=attempt_start,
                    end_date=attempt_end,
                    rng=rng,
                )
            )

            redemption_date = (
                redemption_timestamp.date()
            )

            historical_tier = tier_on_date(
                member_id=member[
                    "member_id"
                ],
                target_date=redemption_date,
                tier_history=tier_history,
            )

            available_benefits = (
                benefits_for_tier(
                    historical_tier
                )
            )

            if not available_benefits:
                raise ValueError(
                    f"{member['member_id']}: "
                    "no benefits available for "
                    f"historical tier "
                    f"{historical_tier}"
                )

            benefit_code = (
                rng.choice(
                    available_benefits
                )
            )

            status = choose_status(
                redemption_date=(
                    redemption_date
                ),
                eligible_until=(
                    eligible_until
                ),
                rng=rng,
            )

            rows.append(
                {
                    "redemption_id": "",
                    "member_id": member[
                        "member_id"
                    ],
                    "benefit_code": (
                        benefit_code
                    ),
                    "redemption_timestamp": (
                        redemption_timestamp.isoformat()
                    ),
                    "redemption_status": (
                        status
                    ),
                    "monetary_value": (
                        monetary_value(
                            benefit_code,
                            status,
                        )
                    ),
                }
            )

    rows.sort(
        key=lambda row: (
            row[
                "redemption_timestamp"
            ],
            row["member_id"],
            row["benefit_code"],
            row[
                "redemption_status"
            ],
        )
    )

    for number, row in enumerate(
        rows,
        start=1,
    ):
        row["redemption_id"] = (
            f"BR{number:07d}"
        )

    return rows

def write_csv(
    path: Path,
    rows: list[dict],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "redemption_id",
        "member_id",
        "benefit_code",
        "redemption_timestamp",
        "redemption_status",
        "monetary_value",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def count_values(
    rows: list[dict],
    field_name: str,
) -> Counter:
    return Counter(
        row[field_name]
        for row in rows
    )


def main() -> None:
    args = parse_args()

    database_path = resolve_path(
        args.database
    )

    output_path = resolve_path(
        args.output
    )

    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: "
            f"{database_path}"
        )

    with sqlite3.connect(
        database_path
    ) as connection:
        members = load_members(
            connection
        )

        suspension_dates = (
            load_suspension_dates(
                connection
            )
        )
        tier_history = (
            load_tier_history(
                connection
            )
        )

    if not members:
        raise RuntimeError(
            "No members found. "
            "Load membership data first."
        )

    rows = build_benefit_redemptions(
        members=members,
        suspension_dates=(
            suspension_dates
        ),
        tier_history=(
            tier_history
        ),
        as_of_date=args.as_of_date,
        seed=args.seed,
    )

    write_csv(
        output_path,
        rows,
    )

    status_counts = count_values(
        rows,
        "redemption_status",
    )

    benefit_counts = count_values(
        rows,
        "benefit_code",
    )

    members_with_redemptions = len(
        {
            row["member_id"]
            for row in rows
        }
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "BENEFIT REDEMPTION GENERATOR"
    )
    print("=" * 70)

    print(
        f"Members                  : "
        f"{len(members):,}"
    )

    print(
        f"Members with redemptions : "
        f"{members_with_redemptions:,}"
    )

    print(
        f"Redemptions generated    : "
        f"{len(rows):,}"
    )

    print(
        f"As-of date               : "
        f"{args.as_of_date}"
    )

    print(
        f"Random seed              : "
        f"{args.seed}"
    )

    print()
    print("Redemption status distribution:")

    for status in sorted(
        status_counts
    ):
        print(
            f"  {status:<18} "
            f"{status_counts[status]:>10,}"
        )

    print()
    print("Benefit distribution:")

    for benefit_code in sorted(
        benefit_counts
    ):
        print(
            f"  {benefit_code:<20} "
            f"{benefit_counts[benefit_code]:>10,}"
        )

    print()

    print(
        f"Output                   : "
        f"{output_path}"
    )

    print()
    print("GENERATION: PASS")


if __name__ == "__main__":
    main()