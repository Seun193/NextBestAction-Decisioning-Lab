import argparse
import csv
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"

CAMPAIGNS_PATH = (
    ROOT
    / "data"
    / "membership"
    / "campaign_interactions.csv"
)

REJECTION_REPORT = (
    ROOT
    / "reports"
    / "membership"
    / "campaign_interaction_rejections.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)

MAX_RESPONSE_DAYS = 7


CAMPAIGNS = {
    "MEMBER_NEWS": {
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
        "channels": {
            "EMAIL",
            "APP",
        },
    },
    "BENEFIT_DISCOVERY": {
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
        "channels": {
            "EMAIL",
            "APP",
        },
    },
    "RENEWAL_REMINDER": {
        "tiers": {
            "STANDARD",
            "PLUS",
            "PREMIUM",
        },
        "channels": {
            "EMAIL",
            "APP",
        },
    },
    "PLUS_UPGRADE": {
        "tiers": {
            "STANDARD",
        },
        "channels": {
            "EMAIL",
            "APP",
        },
    },
    "PREMIUM_UPGRADE": {
        "tiers": {
            "PLUS",
        },
        "channels": {
            "EMAIL",
            "APP",
        },
    },
    "PREMIUM_EXPERIENCE": {
        "tiers": {
            "PREMIUM",
        },
        "channels": {
            "EMAIL",
            "APP",
        },
    },
}


VALID_RESPONSE_TYPES = {
    "OPENED",
    "CLICKED",
    "CONVERTED",
    "IGNORED",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate, load, and reconcile synthetic "
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
        "--input",
        type=Path,
        default=CAMPAIGNS_PATH,
        help=(
            "Campaign interaction CSV. "
            f"Default: {CAMPAIGNS_PATH}"
        ),
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


def resolve_path(
    path: Path,
) -> Path:
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


def parse_boolean(
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
            f"{field_name} is not a valid "
            f"ISO timestamp: {value}"
        ) from exc


def load_member_context(
    connection: sqlite3.Connection,
) -> dict[str, dict]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            m.member_id,
            m.membership_status,
            m.join_date,
            m.end_date,
            c.marketing_consent
                AS customer_marketing_consent
        FROM members AS m
        JOIN customers AS c
          ON c.customer_id = m.customer_id
        """
    ).fetchall()

    return {
        row["member_id"]: dict(row)
        for row in rows
    }


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

    history = defaultdict(
        list
    )

    for row in rows:
        if not row["new_tier"]:
            continue

        effective_date = (
            datetime.fromisoformat(
                row["event_timestamp"]
            ).date()
        )

        history[
            row["member_id"]
        ].append(
            (
                effective_date,
                row["new_tier"],
            )
        )

    return dict(
        history
    )


def tier_on_date(
    member_id: str,
    target_date: date,
    tier_history: dict[
        str,
        list[tuple[date, str]],
    ],
) -> str | None:
    tier = None

    for effective_date, new_tier in (
        tier_history.get(
            member_id,
            [],
        )
    ):
        if effective_date > target_date:
            break

        tier = new_tier

    return tier


def lifecycle_end_date(
    member: dict,
    member_id: str,
    suspension_dates: dict[str, date],
    as_of_date: date,
) -> date:
    result = as_of_date

    if member["end_date"]:
        result = min(
            result,
            date.fromisoformat(
                member["end_date"]
            ),
        )

    if (
        member[
            "membership_status"
        ]
        == "SUSPENDED"
    ):
        suspension_date = (
            suspension_dates.get(
                member_id
            )
        )

        if suspension_date:
            result = min(
                result,
                suspension_date,
            )

    return result


def validate_campaign_interactions(
    rows: list[dict],
    members: dict[str, dict],
    suspension_dates: dict[str, date],
    tier_history: dict[
        str,
        list[tuple[date, str]],
    ],
    as_of_date: date,
) -> tuple[
    list[tuple],
    list[dict],
]:
    accepted = []
    rejected = []

    seen_ids = set()

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        interaction_id = row.get(
            "interaction_id",
            "",
        ).strip()

        try:
            if not interaction_id:
                raise ValueError(
                    "interaction_id is missing"
                )

            if not (
                interaction_id.startswith(
                    "CI"
                )
                and len(interaction_id) == 9
                and interaction_id[2:].isdigit()
            ):
                raise ValueError(
                    "interaction_id must match "
                    "CI#######"
                )

            if interaction_id in seen_ids:
                raise ValueError(
                    "duplicate interaction_id "
                    "in source"
                )

            seen_ids.add(
                interaction_id
            )

            campaign_id = row.get(
                "campaign_id",
                "",
            ).strip()

            if not campaign_id:
                raise ValueError(
                    "campaign_id is missing"
                )

            if campaign_id not in CAMPAIGNS:
                raise ValueError(
                    "invalid campaign_id"
                )

            member_id = row.get(
                "member_id",
                "",
            ).strip()

            if member_id not in members:
                raise ValueError(
                    "member_id does not reference "
                    "an existing member"
                )

            member = members[
                member_id
            ]

            if (
                parse_boolean(
                    member[
                        "customer_marketing_consent"
                    ],
                    "customer_marketing_consent",
                )
                != 1
            ):
                raise ValueError(
                    "customer marketing consent "
                    "is not granted"
                )

            channel = row.get(
                "channel",
                "",
            ).strip()

            if (
                channel
                not in CAMPAIGNS[
                    campaign_id
                ]["channels"]
            ):
                raise ValueError(
                    "invalid channel for campaign"
                )

            raw_sent_timestamp = row.get(
                "sent_timestamp",
                "",
            ).strip()

            if not raw_sent_timestamp:
                raise ValueError(
                    "sent_timestamp is missing"
                )

            sent_timestamp = (
                parse_timestamp(
                    raw_sent_timestamp,
                    "sent_timestamp",
                )
            )

            sent_date = (
                sent_timestamp.date()
            )

            join_date = (
                date.fromisoformat(
                    member["join_date"]
                )
            )

            if sent_date < join_date:
                raise ValueError(
                    "campaign sent before "
                    "join_date"
                )

            if sent_date > as_of_date:
                raise ValueError(
                    "campaign sent after "
                    "as-of date"
                )

            lifecycle_end = (
                lifecycle_end_date(
                    member=member,
                    member_id=member_id,
                    suspension_dates=(
                        suspension_dates
                    ),
                    as_of_date=(
                        as_of_date
                    ),
                )
            )

            if sent_date > lifecycle_end:
                raise ValueError(
                    "campaign sent after "
                    "eligible lifecycle"
                )

            historical_tier = (
                tier_on_date(
                    member_id=member_id,
                    target_date=sent_date,
                    tier_history=(
                        tier_history
                    ),
                )
            )

            if historical_tier is None:
                raise ValueError(
                    "no historical tier "
                    "at send time"
                )

            if (
                historical_tier
                not in CAMPAIGNS[
                    campaign_id
                ]["tiers"]
            ):
                raise ValueError(
                    "campaign is not valid "
                    "for historical tier"
                )

            response_type = row.get(
                "response_type",
                "",
            ).strip()

            raw_response_timestamp = (
                row.get(
                    "response_timestamp",
                    "",
                ).strip()
            )

            #
            # Schema permits NULL response_type.
            # This represents an interaction that
            # has not yet been classified.
            #
            if response_type == "":
                if raw_response_timestamp:
                    raise ValueError(
                        "response_timestamp requires "
                        "response_type"
                    )

                normalized_response_type = None
                normalized_response_timestamp = None

            elif (
                response_type
                not in VALID_RESPONSE_TYPES
            ):
                raise ValueError(
                    "invalid response_type"
                )

            elif response_type == "IGNORED":
                if raw_response_timestamp:
                    raise ValueError(
                        "IGNORED must not have "
                        "response_timestamp"
                    )

                normalized_response_type = (
                    response_type
                )

                normalized_response_timestamp = None

            else:
                if not raw_response_timestamp:
                    raise ValueError(
                        f"{response_type} requires "
                        "response_timestamp"
                    )

                response_timestamp = (
                    parse_timestamp(
                        raw_response_timestamp,
                        "response_timestamp",
                    )
                )

                if (
                    response_timestamp
                    <= sent_timestamp
                ):
                    raise ValueError(
                        "response_timestamp must "
                        "be after sent_timestamp"
                    )

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

                if (
                    response_timestamp
                    > latest_response
                ):
                    raise ValueError(
                        "response_timestamp exceeds "
                        "allowed response window"
                    )

                normalized_response_type = (
                    response_type
                )

                normalized_response_timestamp = (
                    response_timestamp.isoformat()
                )

            accepted.append(
                (
                    interaction_id,
                    campaign_id,
                    member_id,
                    channel,
                    sent_timestamp.isoformat(),
                    normalized_response_type,
                    normalized_response_timestamp,
                )
            )

        except (
            KeyError,
            ValueError,
        ) as exc:
            rejected.append(
                {
                    "source": (
                        "campaign_interactions"
                    ),
                    "source_row_number": (
                        row_number
                    ),
                    "record_id": (
                        interaction_id
                    ),
                    "reason": str(
                        exc
                    ),
                }
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


def insert_campaign_interactions(
    connection: sqlite3.Connection,
    rows: list[tuple],
) -> None:
    connection.executemany(
        """
        INSERT INTO campaign_interactions (
            interaction_id,
            campaign_id,
            member_id,
            channel,
            sent_timestamp,
            response_type,
            response_timestamp
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?
        )
        """,
        rows,
    )


def rejection_summary(
    rejected_rows: list[dict],
) -> Counter:
    return Counter(
        row["reason"]
        for row in rejected_rows
    )


def main() -> None:
    args = parse_args()

    database_path = resolve_path(
        args.database
    )

    input_path = resolve_path(
        args.input
    )

    rejection_path = resolve_path(
        args.rejections
    )

    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: "
            f"{database_path}"
        )

    rows = read_csv(
        input_path
    )

    start = perf_counter()

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        members = (
            load_member_context(
                connection
            )
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

        accepted, rejected = (
            validate_campaign_interactions(
                rows=rows,
                members=members,
                suspension_dates=(
                    suspension_dates
                ),
                tier_history=(
                    tier_history
                ),
                as_of_date=(
                    args.as_of_date
                ),
            )
        )

        #
        # This loader owns only
        # campaign_interactions.
        #
        connection.execute(
            """
            DELETE FROM campaign_interactions
            """
        )

        insert_campaign_interactions(
            connection,
            accepted,
        )

        connection.commit()

        database_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM campaign_interactions
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
        rejected,
    )

    elapsed = (
        perf_counter()
        - start
    )

    source_count = len(
        rows
    )

    accepted_count = len(
        accepted
    )

    rejected_count = len(
        rejected
    )

    if (
        source_count
        != accepted_count
        + rejected_count
    ):
        raise RuntimeError(
            "Source reconciliation failed: "
            "source rows do not equal "
            "accepted + rejected."
        )

    if (
        database_count
        != accepted_count
    ):
        raise RuntimeError(
            "Database reconciliation failed: "
            "database rows do not equal "
            "accepted rows."
        )

    if foreign_key_errors:
        raise RuntimeError(
            "Foreign-key reconciliation failed."
        )

    summary = rejection_summary(
        rejected
    )

    print("=" * 70)

    print(
        "NBA DECISIONING LAB - "
        "CAMPAIGN INTERACTION INGESTION"
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

    if not summary:
        print("  None")
    else:
        for reason, count in sorted(
            summary.items()
        ):
            print(
                f"  {reason:<45} "
                f"{count:>8,}"
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

    print(
        "RECONCILIATION: PASS"
    )


if __name__ == "__main__":
    main()