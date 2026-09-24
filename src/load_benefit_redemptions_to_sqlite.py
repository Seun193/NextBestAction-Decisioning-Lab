import argparse
import csv
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"

REDEMPTIONS_PATH = (
    ROOT
    / "data"
    / "membership"
    / "benefit_redemptions.csv"
)

REJECTION_REPORT = (
    ROOT
    / "reports"
    / "membership"
    / "benefit_redemption_rejections.csv"
)

DEFAULT_AS_OF_DATE = date(2026, 9, 21)

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


VALID_STATUSES = {
    "REDEEMED",
    "REVERSED",
    "FAILED",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate, load, and reconcile "
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
        "--redemptions",
        type=Path,
        default=REDEMPTIONS_PATH,
        help=(
            "Benefit redemption CSV. "
            f"Default: {REDEMPTIONS_PATH}"
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


def load_member_reference(
    connection: sqlite3.Connection,
) -> dict[str, dict]:
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            member_id,
            membership_status,
            join_date,
            end_date
        FROM members
        """
    ).fetchall()

    return {
        row["member_id"]: dict(row)
        for row in rows
    }


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
        new_tier = row[
            "new_tier"
        ]

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
            "no historical membership tier "
            f"found for {target_date}"
        )

    return current_tier


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
        f"unsupported membership status: "
        f"{status}"
    )


def validate_redemption_id(
    redemption_id: str,
) -> None:
    if not redemption_id:
        raise ValueError(
            "redemption_id is missing"
        )

    if not (
        redemption_id.startswith("BR")
        and len(redemption_id) == 9
        and redemption_id[2:].isdigit()
    ):
        raise ValueError(
            "redemption_id must match BR#######"
        )


def parse_monetary_value(
    raw_value: str,
    status: str,
    expected_value: float,
) -> float | None:
    raw_value = raw_value.strip()

    if status == "FAILED":
        if raw_value:
            raise ValueError(
                "FAILED redemption must not "
                "have monetary_value"
            )

        return None

    if not raw_value:
        raise ValueError(
            f"{status} redemption requires "
            "monetary_value"
        )

    try:
        value = float(
            raw_value
        )
    except ValueError as exc:
        raise ValueError(
            "monetary_value is not numeric"
        ) from exc

    if value < 0:
        raise ValueError(
            "monetary_value cannot be negative"
        )

    if value != expected_value:
        raise ValueError(
            "monetary_value does not match "
            "benefit definition"
        )

    return value


def reject(
    rejected_rows: list[dict],
    source_row_number: int,
    record_id: str,
    reason: str,
) -> None:
    rejected_rows.append(
        {
            "source": "benefit_redemptions",
            "source_row_number": (
                source_row_number
            ),
            "record_id": record_id,
            "reason": reason,
        }
    )


def validate_benefit_redemptions(
    rows: list[dict],
    members: dict[str, dict],
    suspension_dates: dict[str, date],
    tier_history: dict[
        str,
        list[tuple[date, str]],
    ],
    as_of_date: date,
) -> tuple[list[tuple], list[dict]]:
    accepted = []
    rejected = []

    seen_redemption_ids: set[str] = set()

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        redemption_id = row.get(
            "redemption_id",
            "",
        ).strip()

        try:
            validate_redemption_id(
                redemption_id
            )

            if (
                redemption_id
                in seen_redemption_ids
            ):
                raise ValueError(
                    "duplicate redemption_id "
                    "in source"
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
                    "member_id does not exist "
                    "in members"
                )

            benefit_code = row.get(
                "benefit_code",
                "",
            ).strip()

            if benefit_code not in BENEFITS:
                raise ValueError(
                    "invalid benefit_code"
                )

            raw_timestamp = row.get(
                "redemption_timestamp",
                "",
            ).strip()

            if not raw_timestamp:
                raise ValueError(
                    "redemption_timestamp is missing"
                )

            redemption_timestamp = (
                parse_timestamp(
                    raw_timestamp,
                    "redemption_timestamp",
                )
            )

            redemption_date = (
                redemption_timestamp.date()
            )

            status = row.get(
                "redemption_status",
                "",
            ).strip()

            if status not in VALID_STATUSES:
                raise ValueError(
                    "invalid redemption_status"
                )

            member = members[
                member_id
            ]

            join_date = date.fromisoformat(
                member["join_date"]
            )

            if redemption_date < join_date:
                raise ValueError(
                    "redemption precedes "
                    "member join_date"
                )

            if redemption_date > as_of_date:
                raise ValueError(
                    "redemption exceeds "
                    "as-of date"
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

            #
            # Successful/redemption-derived outcomes
            # must occur while the member is eligible.
            #
            if (
                status
                in {
                    "REDEEMED",
                    "REVERSED",
                }
                and redemption_date
                > eligible_until
            ):
                raise ValueError(
                    f"{status} redemption occurs "
                    "after eligibility ended"
                )

            #
            # Failed attempts are retained for
            # operational evidence, but only within
            # the supported post-eligibility window.
            #
            if (
                status == "FAILED"
                and redemption_date
                > eligible_until
                + timedelta(
                    days=(
                        POST_ELIGIBILITY_ATTEMPT_DAYS
                    )
                )
            ):
                raise ValueError(
                    "FAILED redemption exceeds "
                    "post-eligibility attempt window"
                )

            historical_tier = (
                tier_on_date(
                    member_id=member_id,
                    target_date=(
                        redemption_date
                    ),
                    tier_history=(
                        tier_history
                    ),
                )
            )

            if (
                historical_tier
                not in BENEFITS[
                    benefit_code
                ]["tiers"]
            ):
                raise ValueError(
                    f"{benefit_code} is not "
                    "available for historical "
                    f"tier {historical_tier}"
                )

            value = (
                parse_monetary_value(
                    raw_value=row.get(
                        "monetary_value",
                        "",
                    ),
                    status=status,
                    expected_value=(
                        BENEFITS[
                            benefit_code
                        ]["value"]
                    ),
                )
            )

            accepted.append(
                (
                    redemption_id,
                    member_id,
                    benefit_code,
                    redemption_timestamp.isoformat(),
                    status,
                    value,
                )
            )

            seen_redemption_ids.add(
                redemption_id
            )

        except (
            KeyError,
            ValueError,
        ) as exc:
            reject(
                rejected_rows=rejected,
                source_row_number=row_number,
                record_id=redemption_id,
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


def insert_redemptions(
    connection: sqlite3.Connection,
    rows: list[tuple],
) -> None:
    connection.executemany(
        """
        INSERT INTO benefit_redemptions (
            redemption_id,
            member_id,
            benefit_code,
            redemption_timestamp,
            redemption_status,
            monetary_value
        )
        VALUES (?, ?, ?, ?, ?, ?)
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

    redemptions_path = resolve_path(
        args.redemptions
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
        redemptions_path
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.row_factory = (
            sqlite3.Row
        )

        members = load_member_reference(
            connection
        )

        if not members:
            raise RuntimeError(
                "No members found. "
                "Load membership data first."
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

        (
            accepted_rows,
            rejected_rows,
        ) = validate_benefit_redemptions(
            rows=source_rows,
            members=members,
            suspension_dates=(
                suspension_dates
            ),
            tier_history=tier_history,
            as_of_date=args.as_of_date,
        )

        #
        # This loader owns only the
        # benefit_redemptions domain.
        #
        connection.execute(
            "DELETE FROM benefit_redemptions"
        )

        insert_redemptions(
            connection,
            accepted_rows,
        )

        connection.commit()

        database_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM benefit_redemptions
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
            "Benefit-redemption reconciliation "
            "failed: source != accepted + rejected."
        )

    if (
        database_count
        != accepted_count
    ):
        raise RuntimeError(
            "Benefit-redemption database count "
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
        "BENEFIT REDEMPTION INGESTION"
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