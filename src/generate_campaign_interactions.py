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
    / "campaign_interactions.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)
DEFAULT_SEED = 210

LOOKBACK_DAYS = 180
MAX_RESPONSE_DAYS = 7


CAMPAIGNS = {
    "MEMBER_NEWS": {
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
        "channels": (
            "EMAIL",
            "APP",
        ),
    },
    "BENEFIT_DISCOVERY": {
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
        "channels": (
            "EMAIL",
            "APP",
        ),
    },
    "RENEWAL_REMINDER": {
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
        "channels": (
            "EMAIL",
            "APP",
        ),
    },
    "PLUS_UPGRADE": {
        "tiers": {
            "STANDARD",
        },
        "channels": (
            "EMAIL",
            "APP",
        ),
    },
    "PREMIUM_UPGRADE": {
        "tiers": {
            "PLUS",
        },
        "channels": (
            "EMAIL",
            "APP",
        ),
    },
    "PREMIUM_EXPERIENCE": {
        "tiers": {
            "PREMIUM",
        },
        "channels": (
            "EMAIL",
            "APP",
        ),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic synthetic "
            "membership campaign interactions."
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


def resolve_path(
    path: Path,
) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path

def parse_consent(
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

def load_members(
    connection: sqlite3.Connection,
) -> list[dict]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            m.member_id,
            m.customer_id,
            m.membership_status,
            m.membership_tier,
            m.join_date,
            m.end_date,
            m.marketing_consent
                AS membership_marketing_consent,
            c.marketing_consent
                AS customer_marketing_consent
        FROM members AS m
        JOIN customers AS c
          ON c.customer_id = m.customer_id
        ORDER BY m.member_id
        """
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def load_suspension_dates(
    connection: sqlite3.Connection,
) -> dict[str, date]:
    rows = connection.execute(
        """
        SELECT
            member_id,
            MAX(event_timestamp)
        FROM membership_events
        WHERE event_type = 'SUSPENDED'
        GROUP BY member_id
        """
    ).fetchall()

    result = {}

    for member_id, raw_timestamp in rows:
        if not raw_timestamp:
            continue

        result[member_id] = (
            datetime.fromisoformat(
                raw_timestamp
            ).date()
        )

    return result


def load_tier_history(
    connection: sqlite3.Connection,
) -> dict[str, list[tuple[date, str]]]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            member_id,
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
        if not row["new_tier"]:
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
                row["new_tier"],
            )
        )

    return history


def load_engagement_counts(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT
            member_id,
            COUNT(*)
        FROM engagement_events
        GROUP BY member_id
        """
    ).fetchall()

    return {
        member_id: count
        for member_id, count in rows
    }


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
            f"{member_id}: no historical tier "
            f"found for {target_date}"
        )

    return current_tier


def campaign_end_date(
    member: dict,
    suspension_dates: dict[str, date],
    as_of_date: date,
) -> date:
    if member["end_date"]:
        return min(
            date.fromisoformat(
                member["end_date"]
            ),
            as_of_date,
        )

    if (
        member["membership_status"]
        == "SUSPENDED"
    ):
        suspension_date = (
            suspension_dates.get(
                member["member_id"]
            )
        )

        if suspension_date:
            return min(
                suspension_date,
                as_of_date,
            )

    return as_of_date


def campaign_count(
    member: dict,
    rng: random.Random,
) -> int:
    status = member[
        "membership_status"
    ]

    if status == "ACTIVE":
        return rng.randint(
            1,
            4,
        )

    if status == "SUSPENDED":
        return rng.randint(
            0,
            2,
        )

    if status in {
        "INACTIVE",
        "CANCELLED",
    }:
        return rng.randint(
            0,
            2,
        )

    raise ValueError(
        f"Unsupported membership status: "
        f"{status}"
    )


def campaigns_for_tier(
    tier: str,
) -> list[str]:
    return [
        campaign_id
        for campaign_id, definition
        in CAMPAIGNS.items()
        if tier in definition["tiers"]
    ]


def random_send_timestamp(
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

    send_date = (
        start_date
        + timedelta(
            days=day_offset
        )
    )

    send_time = time(
        hour=rng.randint(
            8,
            20,
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
        send_date,
        send_time,
    )


def choose_response_type(
    engagement_count: int,
    rng: random.Random,
) -> str:
    #
    # Previous engagement makes a response
    # somewhat more likely without making
    # conversion unrealistically dominant.
    #
    engagement_factor = min(
        engagement_count / 10,
        1.0,
    )

    conversion_probability = (
        0.035
        + (0.025 * engagement_factor)
    )

    click_probability = (
        0.10
        + (0.06 * engagement_factor)
    )

    open_probability = (
        0.30
        + (0.10 * engagement_factor)
    )

    roll = rng.random()

    if roll < conversion_probability:
        return "CONVERTED"

    if (
        roll
        < conversion_probability
        + click_probability
    ):
        return "CLICKED"

    if (
        roll
        < conversion_probability
        + click_probability
        + open_probability
    ):
        return "OPENED"

    return "IGNORED"


def response_timestamp(
    sent_timestamp: datetime,
    response_type: str,
    as_of_date: date,
    rng: random.Random,
) -> str:
    if response_type == "IGNORED":
        return ""

    as_of_end = datetime.combine(
        as_of_date,
        time(
            hour=23,
            minute=59,
            second=59,
        ),
    )

    latest_response = min(
        sent_timestamp
        + timedelta(
            days=MAX_RESPONSE_DAYS
        ),
        as_of_end,
    )

    available_seconds = int(
        (
            latest_response
            - sent_timestamp
        ).total_seconds()
    )

    if available_seconds <= 0:
        raise ValueError(
            "No valid response window "
            "after sent_timestamp"
        )

    offset_seconds = rng.randint(
        1,
        available_seconds,
    )

    return (
        sent_timestamp
        + timedelta(
            seconds=offset_seconds
        )
    ).isoformat()


def build_campaign_interactions(
    members: list[dict],
    suspension_dates: dict[str, date],
    tier_history: dict[
        str,
        list[tuple[date, str]],
    ],
    engagement_counts: dict[str, int],
    as_of_date: date,
    seed: int,
) -> list[dict]:
    rng = random.Random(
        seed
    )

    rows = []

    reporting_start = (
        as_of_date
        - timedelta(
            days=LOOKBACK_DAYS
        )
    )

    for member in members:
        #
        # MDO-015:
        # customer-system consent is authoritative.
        #
        if (
            parse_consent(
                member[
                    "customer_marketing_consent"
                ],
                "customer_marketing_consent",
            )
            != 1
        ):
            continue    
        member_id = member[
            "member_id"
        ]

        join_date = date.fromisoformat(
            member["join_date"]
        )

        send_start = max(
            join_date,
            reporting_start,
        )

        send_end = campaign_end_date(
            member=member,
            suspension_dates=(
                suspension_dates
            ),
            as_of_date=as_of_date,
        )

        #
        # Members whose eligible marketing
        # lifecycle ended before the reporting
        # window receive no generated sends.
        #
        if send_end < send_start:
            continue

        number_of_campaigns = (
            campaign_count(
                member,
                rng,
            )
        )

        for _ in range(
            number_of_campaigns
        ):
            sent_timestamp = (
                random_send_timestamp(
                    start_date=send_start,
                    end_date=send_end,
                    rng=rng,
                )
            )

            historical_tier = (
                tier_on_date(
                    member_id=member_id,
                    target_date=(
                        sent_timestamp.date()
                    ),
                    tier_history=(
                        tier_history
                    ),
                )
            )

            available_campaigns = (
                campaigns_for_tier(
                    historical_tier
                )
            )

            if not available_campaigns:
                raise ValueError(
                    f"{member_id}: no campaigns "
                    f"available for tier "
                    f"{historical_tier}"
                )

            campaign_id = rng.choice(
                available_campaigns
            )

            channel = rng.choice(
                CAMPAIGNS[
                    campaign_id
                ]["channels"]
            )

            response_type = (
                choose_response_type(
                    engagement_count=(
                        engagement_counts.get(
                            member_id,
                            0,
                        )
                    ),
                    rng=rng,
                )
            )

            response_time = (
                response_timestamp(
                    sent_timestamp=(
                        sent_timestamp
                    ),
                    response_type=(
                        response_type
                    ),
                    as_of_date=as_of_date,
                    rng=rng,
                )
            )

            rows.append(
                {
                    "interaction_id": "",
                    "campaign_id": (
                        campaign_id
                    ),
                    "member_id": (
                        member_id
                    ),
                    "channel": channel,
                    "sent_timestamp": (
                        sent_timestamp.isoformat()
                    ),
                    "response_type": (
                        response_type
                    ),
                    "response_timestamp": (
                        response_time
                    ),
                }
            )

    rows.sort(
        key=lambda row: (
            row["sent_timestamp"],
            row["member_id"],
            row["campaign_id"],
            row["channel"],
        )
    )

    for number, row in enumerate(
        rows,
        start=1,
    ):
        row["interaction_id"] = (
            f"CI{number:07d}"
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
        "interaction_id",
        "campaign_id",
        "member_id",
        "channel",
        "sent_timestamp",
        "response_type",
        "response_timestamp",
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

        engagement_counts = (
            load_engagement_counts(
                connection
            )
        )

    if not members:
        raise RuntimeError(
            "No members found. "
            "Load membership data first."
        )

    rows = build_campaign_interactions(
        members=members,
        suspension_dates=(
            suspension_dates
        ),
        tier_history=tier_history,
        engagement_counts=(
            engagement_counts
        ),
        as_of_date=args.as_of_date,
        seed=args.seed,
    )

    write_csv(
        output_path,
        rows,
    )

    response_counts = count_values(
        rows,
        "response_type",
    )

    campaign_counts = count_values(
        rows,
        "campaign_id",
    )

    channel_counts = count_values(
        rows,
        "channel",
    )

    customer_opt_in_count = sum(
        1
        for member in members
        if parse_consent(
            member[
                "customer_marketing_consent"
            ],
            "customer_marketing_consent",
        )
        == 1
    )

    
    suppressed_count = (
        len(members)
        - customer_opt_in_count
    )

    consent_mismatches = sum(
        1
        for member in members
        if parse_consent(
            member[
                "membership_marketing_consent"
            ],
            "membership_marketing_consent",
        )
        != parse_consent(
            member[
                "customer_marketing_consent"
            ],
            "customer_marketing_consent",
        )
    )

    members_contacted = len(
        {
            row["member_id"]
            for row in rows
        }
    )

    converted_count = (
        response_counts[
            "CONVERTED"
        ]
    )

    conversion_rate = (
        converted_count
        / len(rows)
        if rows
        else 0
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "CAMPAIGN INTERACTION GENERATOR"
    )
    print("=" * 70)

    print(
        f"Members                  : "
        f"{len(members):,}"
    )

    print(
        f"Customer consent = 1     : "
        f"{customer_opt_in_count:,}"
    )

    print(
        f"Suppressed by authority  : "
        f"{suppressed_count:,}"
    )

    print(
        f"Consent mismatches       : "
        f"{consent_mismatches:,}"
    )

    print(
        f"Members contacted        : "
        f"{members_contacted:,}"
    )

    print(
        f"Interactions generated   : "
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
    print("Response distribution:")

    for response_type in sorted(
        response_counts
    ):
        print(
            f"  {response_type:<18} "
            f"{response_counts[response_type]:>10,}"
        )

    print()

    print(
        f"Conversion rate          : "
        f"{conversion_rate:.2%}"
    )

    print()
    print("Campaign distribution:")

    for campaign_id in sorted(
        campaign_counts
    ):
        print(
            f"  {campaign_id:<22} "
            f"{campaign_counts[campaign_id]:>10,}"
        )

    print()
    print("Channel distribution:")

    for channel in sorted(
        channel_counts
    ):
        print(
            f"  {channel:<10} "
            f"{channel_counts[channel]:>10,}"
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