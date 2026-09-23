import argparse
import csv
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"

OUTPUT_PATH = (
    ROOT
    / "data"
    / "membership"
    / "membership_events.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)


PLAN_TO_TIER = {
    "MEMBERSHIP_STANDARD": "STANDARD",
    "MEMBERSHIP_PLUS": "PLUS",
    "MEMBERSHIP_PREMIUM": "PREMIUM",
}

TIER_RANK = {
    "STANDARD": 1,
    "PLUS": 2,
    "PREMIUM": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate lifecycle-consistent membership events "
            "from the current membership database."
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

    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def timestamp(
    event_date: date,
    hour: int = 9,
) -> str:
    value = datetime.combine(
        event_date,
        time(hour=hour),
    )

    return value.isoformat()


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

    return [dict(row) for row in rows]


def load_subscriptions(
    connection: sqlite3.Connection,
) -> dict[str, list[dict]]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            subscription_id,
            member_id,
            plan_name,
            start_date,
            end_date,
            renewal_status
        FROM subscriptions
        ORDER BY
            member_id,
            start_date,
            subscription_id
        """
    ).fetchall()

    grouped: dict[str, list[dict]] = {}

    for row in rows:
        record = dict(row)

        grouped.setdefault(
            record["member_id"],
            [],
        ).append(record)

    return grouped


def lifecycle_end_date(
    member: dict,
    as_of_date: date,
) -> date:
    raw_end_date = member["end_date"]

    if raw_end_date:
        return date.fromisoformat(
            raw_end_date
        )

    return as_of_date


def tier_from_plan(
    plan_name: str,
) -> str:
    try:
        return PLAN_TO_TIER[plan_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown membership plan: {plan_name}"
        ) from exc


def append_event(
    events: list[dict],
    member_id: str,
    event_type: str,
    event_date: date,
    previous_tier: str = "",
    new_tier: str = "",
    notes: str = "",
    hour: int = 9,
) -> None:
    events.append(
        {
            "event_id": "",
            "member_id": member_id,
            "event_type": event_type,
            "event_timestamp": timestamp(
                event_date,
                hour,
            ),
            "previous_tier": previous_tier,
            "new_tier": new_tier,
            "notes": notes,
        }
    )


def add_join_event(
    events: list[dict],
    member: dict,
    subscriptions: list[dict],
) -> None:
    join_date = date.fromisoformat(
        member["join_date"]
    )

    original_tier = (
        tier_from_plan(
            subscriptions[0]["plan_name"]
        )
        if subscriptions
        else member["membership_tier"]
    )

    append_event(
        events=events,
        member_id=member["member_id"],
        event_type="JOINED",
        event_date=join_date,
        new_tier=original_tier,
        notes="Membership created",
        hour=9,
    )


def add_renewal_events(
    events: list[dict],
    member: dict,
    as_of_date: date,
) -> None:
    join_date = date.fromisoformat(
        member["join_date"]
    )

    end_date = lifecycle_end_date(
        member,
        as_of_date,
    )

    anniversary_year = join_date.year + 1

    while True:
        try:
            anniversary = join_date.replace(
                year=anniversary_year
            )
        except ValueError:
            anniversary = date(
                anniversary_year,
                2,
                28,
            )

        if anniversary >= end_date:
            break

        append_event(
            events=events,
            member_id=member["member_id"],
            event_type="RENEWED",
            event_date=anniversary,
            notes="Annual membership renewal",
            hour=10,
        )

        anniversary_year += 1


def add_tier_change_events(
    events: list[dict],
    member: dict,
    subscriptions: list[dict],
) -> None:
    if len(subscriptions) < 2:
        return

    previous_subscription = (
        subscriptions[0]
    )

    for current_subscription in subscriptions[1:]:
        previous_tier = tier_from_plan(
            previous_subscription["plan_name"]
        )

        new_tier = tier_from_plan(
            current_subscription["plan_name"]
        )

        if previous_tier == new_tier:
            previous_subscription = (
                current_subscription
            )
            continue

        event_date = date.fromisoformat(
            current_subscription["start_date"]
        )

        if (
            TIER_RANK[new_tier]
            > TIER_RANK[previous_tier]
        ):
            event_type = "UPGRADED"
        else:
            event_type = "DOWNGRADED"

        append_event(
            events=events,
            member_id=member["member_id"],
            event_type=event_type,
            event_date=event_date,
            previous_tier=previous_tier,
            new_tier=new_tier,
            notes=(
                f"Plan changed from "
                f"{previous_tier} to {new_tier}"
            ),
            hour=11,
        )

        previous_subscription = (
            current_subscription
        )


def add_terminal_status_event(
    events: list[dict],
    member: dict,
    as_of_date: date,
) -> None:
    status = member["membership_status"]
    member_id = member["member_id"]

    if status == "CANCELLED":
        if not member["end_date"]:
            raise ValueError(
                f"{member_id} is CANCELLED "
                "without end_date"
            )

        cancellation_date = date.fromisoformat(
            member["end_date"]
        )

        append_event(
            events=events,
            member_id=member_id,
            event_type="CANCELLED",
            event_date=cancellation_date,
            previous_tier=member[
                "membership_tier"
            ],
            notes="Membership cancelled",
            hour=17,
        )

    elif status == "SUSPENDED":
        join_date = date.fromisoformat(
            member["join_date"]
        )

        proposed_date = (
            as_of_date
            - timedelta(days=30)
        )

        suspension_date = max(
            join_date,
            proposed_date,
        )

        append_event(
            events=events,
            member_id=member_id,
            event_type="SUSPENDED",
            event_date=suspension_date,
            previous_tier=member[
                "membership_tier"
            ],
            notes=(
                "Membership suspended "
                "as of reporting period"
            ),
            hour=14,
        )


def assign_event_ids(
    events: list[dict],
) -> None:
    events.sort(
        key=lambda event: (
            event["event_timestamp"],
            event["member_id"],
            event["event_type"],
        )
    )

    for number, event in enumerate(
        events,
        start=1,
    ):
        event["event_id"] = (
            f"ME{number:07d}"
        )


def build_membership_events(
    members: list[dict],
    subscriptions_by_member: dict[
        str,
        list[dict],
    ],
    as_of_date: date,
) -> list[dict]:
    events: list[dict] = []

    for member in members:
        member_id = member["member_id"]

        subscriptions = (
            subscriptions_by_member.get(
                member_id,
                [],
            )
        )

        add_join_event(
            events,
            member,
            subscriptions,
        )

        add_renewal_events(
            events,
            member,
            as_of_date,
        )

        add_tier_change_events(
            events,
            member,
            subscriptions,
        )

        add_terminal_status_event(
            events,
            member,
            as_of_date,
        )

    assign_event_ids(events)

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
        "previous_tier",
        "new_tier",
        "notes",
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


def event_counts(
    events: list[dict],
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for event in events:
        event_type = event["event_type"]

        counts[event_type] = (
            counts.get(event_type, 0)
            + 1
        )

    return dict(
        sorted(counts.items())
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

        subscriptions_by_member = (
            load_subscriptions(
                connection
            )
        )

    if not members:
        raise RuntimeError(
            "No members found. "
            "Load membership data first."
        )

    events = build_membership_events(
        members=members,
        subscriptions_by_member=(
            subscriptions_by_member
        ),
        as_of_date=args.as_of_date,
    )

    write_csv(
        output_path,
        events,
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "MEMBERSHIP EVENT GENERATOR"
    )
    print("=" * 70)

    print(
        f"Members          : "
        f"{len(members):,}"
    )

    print(
        f"Events generated : "
        f"{len(events):,}"
    )

    print(
        f"As-of date       : "
        f"{args.as_of_date}"
    )

    print()
    print("Event distribution:")

    for event_type, count in event_counts(
        events
    ).items():
        print(
            f"  {event_type:<12} "
            f"{count:>10,}"
        )

    print()

    print(
        f"Output           : "
        f"{output_path}"
    )

    print()
    print("GENERATION: PASS")


if __name__ == "__main__":
    main()