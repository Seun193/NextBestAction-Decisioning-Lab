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
    / "engagement_events.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)
DEFAULT_SEED = 126

LOOKBACK_DAYS = 180


EVENT_TYPES = (
    "APP_SESSION",
    "CONTENT_VIEW",
    "EMAIL_OPEN",
    "CAMPAIGN_CLICK",
    "EVENT_REGISTRATION",
    "BENEFIT_VIEW",
)


EVENT_WEIGHTS = (
    32,
    25,
    18,
    8,
    5,
    12,
)


TIER_ACTIVITY_BONUS = {
    "STANDARD": 0,
    "PLUS": 1,
    "PREMIUM": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic synthetic member "
            "engagement events."
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

    suspension_dates = {}

    for member_id, raw_timestamp in rows:
        if not raw_timestamp:
            continue

        suspension_dates[member_id] = (
            datetime.fromisoformat(
                raw_timestamp
            ).date()
        )

    return suspension_dates


def activity_end_date(
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


def engagement_count(
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
            rng.randint(3, 9)
            + tier_bonus
        )

    if status == "SUSPENDED":
        return rng.randint(
            1,
            4,
        )

    if status == "INACTIVE":
        return rng.randint(
            0,
            3,
        )

    if status == "CANCELLED":
        return rng.randint(
            1,
            4,
        )

    raise ValueError(
        f"Unsupported membership status: "
        f"{status}"
    )


def choose_event_type(
    rng: random.Random,
) -> str:
    return rng.choices(
        EVENT_TYPES,
        weights=EVENT_WEIGHTS,
        k=1,
    )[0]


def choose_channel(
    event_type: str,
    rng: random.Random,
) -> str:
    if event_type == "APP_SESSION":
        return "APP"

    if event_type == "EMAIL_OPEN":
        return "EMAIL"

    if event_type == "CAMPAIGN_CLICK":
        return rng.choice(
            [
                "EMAIL",
                "APP",
            ]
        )

    if event_type == "EVENT_REGISTRATION":
        return rng.choice(
            [
                "WEB",
                "APP",
            ]
        )

    if event_type == "BENEFIT_VIEW":
        return rng.choice(
            [
                "APP",
                "WEB",
            ]
        )

    if event_type == "CONTENT_VIEW":
        return rng.choice(
            [
                "APP",
                "WEB",
            ]
        )

    raise ValueError(
        f"Unsupported engagement event type: "
        f"{event_type}"
    )


def random_timestamp(
    start_date: date,
    end_date: date,
    rng: random.Random,
) -> str:
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
        + timedelta(days=day_offset)
    )

    event_time = time(
        hour=rng.randint(7, 22),
        minute=rng.randint(0, 59),
        second=rng.randint(0, 59),
    )

    return datetime.combine(
        event_date,
        event_time,
    ).isoformat()


def build_engagement_events(
    members: list[dict],
    suspension_dates: dict[str, date],
    as_of_date: date,
    seed: int,
) -> list[dict]:
    rng = random.Random(seed)

    events = []

    for member in members:
        member_id = member[
            "member_id"
        ]

        join_date = date.fromisoformat(
            member["join_date"]
        )

        end_date = activity_end_date(
            member=member,
            suspension_dates=(
                suspension_dates
            ),
            as_of_date=as_of_date,
        )

        if end_date < join_date:
            raise ValueError(
                f"{member_id}: activity end "
                "precedes join_date"
            )

        activity_start = max(
            join_date,
            end_date
            - timedelta(
                days=LOOKBACK_DAYS
            ),
        )

        number_of_events = (
            engagement_count(
                member,
                rng,
            )
        )

        for _ in range(
            number_of_events
        ):
            event_type = (
                choose_event_type(
                    rng
                )
            )

            channel = choose_channel(
                event_type,
                rng,
            )

            event_timestamp = (
                random_timestamp(
                    start_date=activity_start,
                    end_date=end_date,
                    rng=rng,
                )
            )

            events.append(
                {
                    "event_id": "",
                    "member_id": member_id,
                    "event_type": (
                        event_type
                    ),
                    "event_timestamp": (
                        event_timestamp
                    ),
                    "channel": channel,
                }
            )

    events.sort(
        key=lambda event: (
            event[
                "event_timestamp"
            ],
            event["member_id"],
            event["event_type"],
            event["channel"],
        )
    )

    for number, event in enumerate(
        events,
        start=1,
    ):
        event["event_id"] = (
            f"EE{number:07d}"
        )

    return events


def write_csv(
    path: Path,
    rows: list[dict],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "event_id",
        "member_id",
        "event_type",
        "event_timestamp",
        "channel",
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
    events: list[dict],
    field_name: str,
) -> Counter:
    return Counter(
        event[field_name]
        for event in events
    )


def members_with_events(
    events: list[dict],
) -> int:
    return len(
        {
            event["member_id"]
            for event in events
        }
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

    if not members:
        raise RuntimeError(
            "No members found. "
            "Load membership data first."
        )

    events = build_engagement_events(
        members=members,
        suspension_dates=(
            suspension_dates
        ),
        as_of_date=args.as_of_date,
        seed=args.seed,
    )

    write_csv(
        output_path,
        events,
    )

    event_counts = count_values(
        events,
        "event_type",
    )

    channel_counts = count_values(
        events,
        "channel",
    )

    engaged_member_count = (
        members_with_events(
            events
        )
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "ENGAGEMENT EVENT GENERATOR"
    )
    print("=" * 70)

    print(
        f"Members              : "
        f"{len(members):,}"
    )

    print(
        f"Members with events  : "
        f"{engaged_member_count:,}"
    )

    print(
        f"Events generated     : "
        f"{len(events):,}"
    )

    print(
        f"As-of date           : "
        f"{args.as_of_date}"
    )

    print(
        f"Random seed          : "
        f"{args.seed}"
    )

    print()
    print("Event distribution:")

    for event_type in sorted(
        event_counts
    ):
        print(
            f"  {event_type:<20} "
            f"{event_counts[event_type]:>10,}"
        )

    print()
    print("Channel distribution:")

    for channel in sorted(
        channel_counts
    ):
        print(
            f"  {channel:<20} "
            f"{channel_counts[channel]:>10,}"
        )

    print()

    print(
        f"Output               : "
        f"{output_path}"
    )

    print()
    print("GENERATION: PASS")


if __name__ == "__main__":
    main()