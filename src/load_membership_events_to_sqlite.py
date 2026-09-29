import argparse
import csv
import sqlite3
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"

EVENTS_PATH = (
    ROOT
    / "data"
    / "membership"
    / "membership_events.csv"
)

REJECTION_REPORT = (
    ROOT
    / "reports"
    / "membership"
    / "membership_event_rejections.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)


VALID_EVENT_TYPES = {
    "JOINED",
    "RENEWED",
    "UPGRADED",
    "DOWNGRADED",
    "SUSPENDED",
    "REACTIVATED",
    "CANCELLED",
}

VALID_TIERS = {
    "STANDARD",
    "PLUS",
    "PREMIUM",
}

TIER_RANK = {
    "STANDARD": 1,
    "PLUS": 2,
    "PREMIUM": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate, load, and reconcile membership "
            "lifecycle events into SQLite."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DB_PATH,
        help=f"SQLite database. Default: {DB_PATH}",
    )

    parser.add_argument(
        "--events",
        type=Path,
        default=EVENTS_PATH,
        help=f"Membership events CSV. Default: {EVENTS_PATH}",
    )

    parser.add_argument(
        "--rejections",
        type=Path,
        default=REJECTION_REPORT,
        help=(
            "Rejected-row evidence CSV. "
            f"Default: {REJECTION_REPORT}"
        ),
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


def read_csv(
    path: Path,
) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Source file not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def parse_timestamp(
    value: str,
    field_name: str,
) -> datetime:
    try:
        return datetime.fromisoformat(
            value
        )
    except ValueError as exc:
        raise ValueError(
            f"{field_name} is not a valid ISO timestamp: "
            f"{value}"
        ) from exc


def load_member_reference(
    connection: sqlite3.Connection,
) -> dict[str, dict]:
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
        """
    ).fetchall()

    return {
        row["member_id"]: dict(row)
        for row in rows
    }


def reject(
    rejected_rows: list[dict],
    source_row_number: int,
    record_id: str,
    reason: str,
) -> None:
    rejected_rows.append(
        {
            "source": "membership_events",
            "source_row_number": source_row_number,
            "record_id": record_id,
            "reason": reason,
        }
    )


def validate_event_id(
    event_id: str,
) -> None:
    if not event_id:
        raise ValueError(
            "event_id is missing"
        )

    if not (
        event_id.startswith("ME")
        and len(event_id) == 9
        and event_id[2:].isdigit()
    ):
        raise ValueError(
            "event_id must match ME#######"
        )


def validate_tier_change(
    event_type: str,
    previous_tier: str,
    new_tier: str,
) -> None:
    if event_type not in {
        "UPGRADED",
        "DOWNGRADED",
    }:
        return

    if not previous_tier:
        raise ValueError(
            f"{event_type} requires previous_tier"
        )

    if not new_tier:
        raise ValueError(
            f"{event_type} requires new_tier"
        )

    if previous_tier == new_tier:
        raise ValueError(
            f"{event_type} tiers must differ"
        )

    if (
        event_type == "UPGRADED"
        and TIER_RANK[new_tier]
        <= TIER_RANK[previous_tier]
    ):
        raise ValueError(
            "UPGRADED event does not increase tier"
        )

    if (
        event_type == "DOWNGRADED"
        and TIER_RANK[new_tier]
        >= TIER_RANK[previous_tier]
    ):
        raise ValueError(
            "DOWNGRADED event does not decrease tier"
        )


def validate_membership_events(
    rows: list[dict],
    members: dict[str, dict],
    as_of_date: date,
) -> tuple[list[tuple], list[dict]]:
    accepted = []
    rejected = []

    seen_event_ids: set[str] = set()

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        event_id = row.get(
            "event_id",
            "",
        ).strip()

        try:
            validate_event_id(
                event_id
            )

            if event_id in seen_event_ids:
                raise ValueError(
                    "duplicate event_id in source"
                )

            member_id = row.get(
                "member_id",
                "",
            ).strip()

            if not member_id:
                raise ValueError(
                    "member_id is missing"
                )

            if member_id not in members:
                raise ValueError(
                    "member_id does not exist in members"
                )

            event_type = row.get(
                "event_type",
                "",
            ).strip()

            if (
                event_type
                not in VALID_EVENT_TYPES
            ):
                raise ValueError(
                    "invalid event_type"
                )

            raw_timestamp = row.get(
                "event_timestamp",
                "",
            ).strip()

            if not raw_timestamp:
                raise ValueError(
                    "event_timestamp is missing"
                )

            event_timestamp = (
                parse_timestamp(
                    raw_timestamp,
                    "event_timestamp",
                )
            )

            event_date = (
                event_timestamp.date()
            )

            member = members[
                member_id
            ]

            join_date = date.fromisoformat(
                member["join_date"]
            )

            lifecycle_end = (
                date.fromisoformat(
                    member["end_date"]
                )
                if member["end_date"]
                else as_of_date
            )

            if event_date < join_date:
                raise ValueError(
                    "event precedes member join_date"
                )

            if event_date > lifecycle_end:
                raise ValueError(
                    "event exceeds member lifecycle"
                )

            previous_tier = row.get(
                "previous_tier",
                "",
            ).strip()

            new_tier = row.get(
                "new_tier",
                "",
            ).strip()

            if (
                previous_tier
                and previous_tier
                not in VALID_TIERS
            ):
                raise ValueError(
                    "invalid previous_tier"
                )

            if (
                new_tier
                and new_tier
                not in VALID_TIERS
            ):
                raise ValueError(
                    "invalid new_tier"
                )

            validate_tier_change(
                event_type=event_type,
                previous_tier=previous_tier,
                new_tier=new_tier,
            )

            if (
                event_type == "JOINED"
                and event_date != join_date
            ):
                raise ValueError(
                    "JOINED event must occur on join_date"
                )

            if event_type == "JOINED":
                if not new_tier:
                    raise ValueError(
                        "JOINED event requires new_tier"
                    )

            if event_type == "CANCELLED":
                member_end_date = (
                    member["end_date"]
                )

                if not member_end_date:
                    raise ValueError(
                        "CANCELLED event requires member end_date"
                    )

                if (
                    event_date
                    != date.fromisoformat(
                        member_end_date
                    )
                ):
                    raise ValueError(
                        "CANCELLED event must occur "
                        "on member end_date"
                    )

            notes = row.get(
                "notes",
                "",
            ).strip()

            accepted.append(
                (
                    event_id,
                    member_id,
                    event_type,
                    event_timestamp.isoformat(),
                    previous_tier or None,
                    new_tier or None,
                    notes or None,
                )
            )

            seen_event_ids.add(
                event_id
            )

        except (
            KeyError,
            ValueError,
        ) as exc:
            reject(
                rejected_rows=rejected,
                source_row_number=row_number,
                record_id=event_id,
                reason=str(exc),
            )

    return accepted, rejected


def write_rejection_report(
    path: Path,
    rejected_rows: list[dict],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "source",
        "source_row_number",
        "record_id",
        "reason",
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

        if rejected_rows:
            writer.writerows(
                rejected_rows
            )


def insert_events(
    connection: sqlite3.Connection,
    rows: list[tuple],
) -> None:
    connection.executemany(
        """
        INSERT INTO membership_events (
            event_id,
            member_id,
            event_type,
            event_timestamp,
            previous_tier,
            new_tier,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def print_rejection_summary(
    rejected_rows: list[dict],
) -> None:
    if not rejected_rows:
        print("  None")
        return

    counts = Counter(
        row["reason"]
        for row in rejected_rows
    )

    for reason, count in (
        counts.most_common()
    ):
        print(
            f"  {count:>6,}  {reason}"
        )


def main() -> None:
    args = parse_args()

    database_path = resolve_path(
        args.database
    )

    events_path = resolve_path(
        args.events
    )

    rejection_path = resolve_path(
        args.rejections
    )

    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: "
            f"{database_path}"
        )

    start = perf_counter()

    source_rows = read_csv(
        events_path
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        members = load_member_reference(
            connection
        )

        if not members:
            raise RuntimeError(
                "No members found. "
                "Load membership data first."
            )

        (
            accepted_rows,
            rejected_rows,
        ) = validate_membership_events(
            rows=source_rows,
            members=members,
            as_of_date=args.as_of_date,
        )

        #
        # This loader owns only the membership_events
        # domain. It does not delete or refresh members,
        # subscriptions, engagement, benefits, or campaigns.
        #
        connection.execute(
            "DELETE FROM membership_events"
        )

        insert_events(
            connection,
            accepted_rows,
        )

        connection.commit()

        database_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM membership_events
                """
            ).fetchone()[0]
        )

        foreign_key_errors = list(
            connection.execute(
                "PRAGMA foreign_key_check"
            )
        )

    write_rejection_report(
        rejection_path,
        rejected_rows,
    )

    source_count = len(
        source_rows
    )

    accepted_count = len(
        accepted_rows
    )

    rejected_count = len(
        rejected_rows
    )

    if (
        source_count
        != accepted_count
        + rejected_count
    ):
        raise RuntimeError(
            "Membership-event reconciliation failed: "
            "source != accepted + rejected."
        )

    if (
        database_count
        != accepted_count
    ):
        raise RuntimeError(
            "Membership-event database count "
            "does not match accepted-source count."
        )

    if foreign_key_errors:
        raise RuntimeError(
            "SQLite foreign-key validation failed: "
            f"{foreign_key_errors}"
        )

    elapsed = (
        perf_counter()
        - start
    )

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "MEMBERSHIP EVENT INGESTION"
    )
    print("=" * 70)

    print(
        f"Source rows       : "
        f"{source_count:,}"
    )

    print(
        f"Accepted rows     : "
        f"{accepted_count:,}"
    )

    print(
        f"Rejected rows     : "
        f"{rejected_count:,}"
    )

    print(
        f"Database rows     : "
        f"{database_count:,}"
    )

    print()
    print("REJECTION SUMMARY")

    print_rejection_summary(
        rejected_rows
    )

    print()

    print(
        f"Rejection report  : "
        f"{rejection_path}"
    )

    print(
        f"Foreign-key errors: "
        f"{len(foreign_key_errors)}"
    )

    print(
        f"Elapsed time      : "
        f"{elapsed:.3f} seconds"
    )

    print()
    print("RECONCILIATION: PASS")


if __name__ == "__main__":
    main()