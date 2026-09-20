import argparse
import csv
import sqlite3
from collections import Counter
from datetime import date
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "nba_lab.db"
MEMBERS_PATH = ROOT / "data" / "membership" / "members.csv"
SUBSCRIPTIONS_PATH = (
    ROOT / "data" / "membership" / "subscriptions.csv"
)

REJECTION_REPORT = (
    ROOT
    / "reports"
    / "membership"
    / "load_rejections.csv"
)


VALID_MEMBER_STATUSES = {
    "ACTIVE",
    "INACTIVE",
    "SUSPENDED",
    "CANCELLED",
}

VALID_MEMBER_TIERS = {
    "STANDARD",
    "PLUS",
    "PREMIUM",
}

VALID_RENEWAL_STATUSES = {
    "NEW",
    "RENEWED",
    "DUE",
    "CANCELLED",
    "EXPIRED",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate, load, and reconcile synthetic "
            "membership source data into SQLite."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DB_PATH,
        help=f"SQLite database. Default: {DB_PATH}",
    )

    parser.add_argument(
        "--members",
        type=Path,
        default=MEMBERS_PATH,
        help=f"Members CSV. Default: {MEMBERS_PATH}",
    )

    parser.add_argument(
        "--subscriptions",
        type=Path,
        default=SUBSCRIPTIONS_PATH,
        help=(
            "Subscriptions CSV. "
            f"Default: {SUBSCRIPTIONS_PATH}"
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

    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Source file not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


def parse_iso_date(
    value: str,
    field_name: str,
) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} is not a valid ISO date: {value}"
        ) from exc


def parse_boolean(
    value: str,
    field_name: str,
) -> int:
    normalized = str(value).strip().lower()

    mappings = {
        "0": 0,
        "1": 1,
        "false": 0,
        "true": 1,
    }

    if normalized not in mappings:
        raise ValueError(
            f"{field_name} must be boolean-style 0/1/true/false"
        )

    return mappings[normalized]


def get_customer_ids(
    connection: sqlite3.Connection,
) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT customer_id FROM customers"
        )
    }


def reject(
    rejected_rows: list[dict],
    source_name: str,
    source_row_number: int,
    record_id: str,
    reason: str,
) -> None:
    rejected_rows.append(
        {
            "source": source_name,
            "source_row_number": source_row_number,
            "record_id": record_id,
            "reason": reason,
        }
    )


def validate_members(
    rows: list[dict],
    customer_ids: set[str],
) -> tuple[list[tuple], list[dict]]:
    accepted = []
    rejected = []

    seen_member_ids: set[str] = set()
    seen_customer_ids: set[str] = set()

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        member_id = row.get(
            "member_id",
            "",
        ).strip()

        customer_id = row.get(
            "customer_id",
            "",
        ).strip()

        try:
            if not member_id:
                raise ValueError(
                    "member_id is missing"
                )

            if not (
                member_id.startswith("M")
                and len(member_id) == 7
                and member_id[1:].isdigit()
            ):
                raise ValueError(
                    "member_id must match M######"
                )

            if member_id in seen_member_ids:
                raise ValueError(
                    "duplicate member_id in source"
                )

            if not customer_id:
                raise ValueError(
                    "customer_id is missing"
                )

            if customer_id in seen_customer_ids:
                raise ValueError(
                    "multiple memberships for customer_id"
                )

            if customer_id not in customer_ids:
                raise ValueError(
                    "customer_id does not exist in customers"
                )

            membership_status = row[
                "membership_status"
            ].strip()

            if (
                membership_status
                not in VALID_MEMBER_STATUSES
            ):
                raise ValueError(
                    "invalid membership_status"
                )

            membership_tier = row[
                "membership_tier"
            ].strip()

            if (
                membership_tier
                not in VALID_MEMBER_TIERS
            ):
                raise ValueError(
                    "invalid membership_tier"
                )

            join_date = parse_iso_date(
                row["join_date"].strip(),
                "join_date",
            )

            raw_end_date = row.get(
                "end_date",
                "",
            ).strip()

            end_date = None

            if raw_end_date:
                end_date = parse_iso_date(
                    raw_end_date,
                    "end_date",
                )

                if end_date < join_date:
                    raise ValueError(
                        "end_date precedes join_date"
                    )

            if (
                membership_status == "ACTIVE"
                and end_date is not None
            ):
                raise ValueError(
                    "ACTIVE member must not have end_date"
                )

            marketing_consent = parse_boolean(
                row["marketing_consent"],
                "marketing_consent",
            )

            created_at = row.get(
                "created_at",
                "",
            ).strip()

            updated_at = row.get(
                "updated_at",
                "",
            ).strip()

            if not created_at:
                raise ValueError(
                    "created_at is missing"
                )

            if not updated_at:
                raise ValueError(
                    "updated_at is missing"
                )

            accepted.append(
                (
                    member_id,
                    customer_id,
                    membership_status,
                    membership_tier,
                    join_date.isoformat(),
                    (
                        end_date.isoformat()
                        if end_date
                        else None
                    ),
                    marketing_consent,
                    created_at,
                    updated_at,
                )
            )

            seen_member_ids.add(member_id)
            seen_customer_ids.add(
                customer_id
            )

        except (
            KeyError,
            ValueError,
        ) as exc:
            reject(
                rejected_rows=rejected,
                source_name="members",
                source_row_number=row_number,
                record_id=member_id,
                reason=str(exc),
            )

    return accepted, rejected


def validate_subscriptions(
    rows: list[dict],
    valid_member_ids: set[str],
) -> tuple[list[tuple], list[dict]]:
    accepted = []
    rejected = []

    seen_subscription_ids: set[str] = set()

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        subscription_id = row.get(
            "subscription_id",
            "",
        ).strip()

        try:
            if not subscription_id:
                raise ValueError(
                    "subscription_id is missing"
                )

            if subscription_id in seen_subscription_ids:
                raise ValueError(
                    "duplicate subscription_id in source"
                )

            member_id = row[
                "member_id"
            ].strip()

            if member_id not in valid_member_ids:
                raise ValueError(
                    "member_id does not reference "
                    "an accepted member"
                )

            plan_name = row[
                "plan_name"
            ].strip()

            if not plan_name:
                raise ValueError(
                    "plan_name is missing"
                )

            start_date = parse_iso_date(
                row["start_date"].strip(),
                "start_date",
            )

            raw_end_date = row.get(
                "end_date",
                "",
            ).strip()

            end_date = None

            if raw_end_date:
                end_date = parse_iso_date(
                    raw_end_date,
                    "end_date",
                )

                if end_date < start_date:
                    raise ValueError(
                        "end_date precedes start_date"
                    )

            renewal_status = row[
                "renewal_status"
            ].strip()

            if (
                renewal_status
                not in VALID_RENEWAL_STATUSES
            ):
                raise ValueError(
                    "invalid renewal_status"
                )

            auto_renew = parse_boolean(
                row["auto_renew"],
                "auto_renew",
            )

            try:
                price = float(
                    row["price"]
                )
            except ValueError as exc:
                raise ValueError(
                    "price is not numeric"
                ) from exc

            if price < 0:
                raise ValueError(
                    "price must not be negative"
                )

            currency = row[
                "currency"
            ].strip()

            if currency != "EUR":
                raise ValueError(
                    "unsupported currency"
                )

            billing_frequency = row[
                "billing_frequency"
            ].strip()

            if not billing_frequency:
                raise ValueError(
                    "billing_frequency is missing"
                )

            accepted.append(
                (
                    subscription_id,
                    member_id,
                    plan_name,
                    start_date.isoformat(),
                    (
                        end_date.isoformat()
                        if end_date
                        else None
                    ),
                    renewal_status,
                    auto_renew,
                    price,
                    currency,
                    billing_frequency,
                )
            )

            seen_subscription_ids.add(
                subscription_id
            )

        except (
            KeyError,
            ValueError,
        ) as exc:
            reject(
                rejected_rows=rejected,
                source_name="subscriptions",
                source_row_number=row_number,
                record_id=subscription_id,
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


def insert_members(
    connection: sqlite3.Connection,
    rows: list[tuple],
) -> None:
    connection.executemany(
        """
        INSERT INTO members (
            member_id,
            customer_id,
            membership_status,
            membership_tier,
            join_date,
            end_date,
            marketing_consent,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def insert_subscriptions(
    connection: sqlite3.Connection,
    rows: list[tuple],
) -> None:
    connection.executemany(
        """
        INSERT INTO subscriptions (
            subscription_id,
            member_id,
            plan_name,
            start_date,
            end_date,
            renewal_status,
            auto_renew,
            price,
            currency,
            billing_frequency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    for reason, count in counts.most_common():
        print(
            f"  {count:>6,}  {reason}"
        )


def main() -> None:
    args = parse_args()

    database_path = resolve_path(
        args.database
    )

    members_path = resolve_path(
        args.members
    )

    subscriptions_path = resolve_path(
        args.subscriptions
    )

    rejection_path = resolve_path(
        args.rejections
    )

    if not database_path.exists():
        raise FileNotFoundError(
            f"Database not found: {database_path}"
        )

    start = perf_counter()

    member_source_rows = read_csv(
        members_path
    )

    subscription_source_rows = read_csv(
        subscriptions_path
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        customer_ids = get_customer_ids(
            connection
        )

        accepted_members, rejected_members = (
            validate_members(
                rows=member_source_rows,
                customer_ids=customer_ids,
            )
        )

        accepted_member_ids = {
            row[0]
            for row in accepted_members
        }

        (
            accepted_subscriptions,
            rejected_subscriptions,
        ) = validate_subscriptions(
            rows=subscription_source_rows,
            valid_member_ids=accepted_member_ids,
        )

        rejected_rows = (
            rejected_members
            + rejected_subscriptions
        )

        #
        # Replace only the membership domains currently
        # controlled by these two source files.
        #
        # Child subscriptions must be deleted first.
        #
        connection.execute(
            "DELETE FROM subscriptions"
        )

        connection.execute(
            "DELETE FROM members"
        )

        insert_members(
            connection,
            accepted_members,
        )

        insert_subscriptions(
            connection,
            accepted_subscriptions,
        )

        connection.commit()

        database_member_count = (
            connection.execute(
                "SELECT COUNT(*) FROM members"
            ).fetchone()[0]
        )

        database_subscription_count = (
            connection.execute(
                "SELECT COUNT(*) FROM subscriptions"
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

    member_source_count = len(
        member_source_rows
    )

    member_accepted_count = len(
        accepted_members
    )

    member_rejected_count = len(
        rejected_members
    )

    subscription_source_count = len(
        subscription_source_rows
    )

    subscription_accepted_count = len(
        accepted_subscriptions
    )

    subscription_rejected_count = len(
        rejected_subscriptions
    )

    if (
        member_source_count
        != member_accepted_count
        + member_rejected_count
    ):
        raise RuntimeError(
            "Member reconciliation failed."
        )

    if (
        subscription_source_count
        != subscription_accepted_count
        + subscription_rejected_count
    ):
        raise RuntimeError(
            "Subscription reconciliation failed."
        )

    if (
        database_member_count
        != member_accepted_count
    ):
        raise RuntimeError(
            "Member database count does not match "
            "accepted-source count."
        )

    if (
        database_subscription_count
        != subscription_accepted_count
    ):
        raise RuntimeError(
            "Subscription database count does not match "
            "accepted-source count."
        )

    if foreign_key_errors:
        raise RuntimeError(
            "SQLite foreign-key validation failed: "
            f"{foreign_key_errors}"
        )

    elapsed = perf_counter() - start

    print("=" * 70)
    print(
        "NBA DECISIONING LAB - "
        "MEMBERSHIP DATA INGESTION"
    )
    print("=" * 70)

    print()
    print("MEMBERS")

    print(
        f"  Source rows   : "
        f"{member_source_count:,}"
    )

    print(
        f"  Accepted rows : "
        f"{member_accepted_count:,}"
    )

    print(
        f"  Rejected rows : "
        f"{member_rejected_count:,}"
    )

    print(
        f"  Database rows : "
        f"{database_member_count:,}"
    )

    print()
    print("SUBSCRIPTIONS")

    print(
        f"  Source rows   : "
        f"{subscription_source_count:,}"
    )

    print(
        f"  Accepted rows : "
        f"{subscription_accepted_count:,}"
    )

    print(
        f"  Rejected rows : "
        f"{subscription_rejected_count:,}"
    )

    print(
        f"  Database rows : "
        f"{database_subscription_count:,}"
    )

    print()
    print("REJECTION SUMMARY")

    print_rejection_summary(
        rejected_rows
    )

    print()
    print(
        f"Rejection report : "
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