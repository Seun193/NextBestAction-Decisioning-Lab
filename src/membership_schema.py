from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "nba_lab.db"


MEMBERSHIP_TABLES = (
    "members",
    "subscriptions",
    "membership_events",
    "engagement_events",
    "benefit_redemptions",
    "campaign_interactions",
)


def create_membership_schema(
    connection: sqlite3.Connection,
) -> None:
    """
    Create the Membership Data Operations schema.

    Existing customer data is preserved.
    Tables are created only when they do not already exist.
    """
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS members (
            member_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL UNIQUE,
            membership_status TEXT NOT NULL
                CHECK (
                    membership_status IN (
                        'ACTIVE',
                        'INACTIVE',
                        'SUSPENDED',
                        'CANCELLED'
                    )
                ),
            membership_tier TEXT NOT NULL
                CHECK (
                    membership_tier IN (
                        'STANDARD',
                        'PLUS',
                        'PREMIUM'
                    )
                ),
            join_date TEXT NOT NULL,
            end_date TEXT,
            marketing_consent INTEGER NOT NULL
                CHECK (marketing_consent IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id),

            CHECK (
                end_date IS NULL
                OR end_date >= join_date
            )
        );


        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            renewal_status TEXT NOT NULL
                CHECK (
                    renewal_status IN (
                        'NEW',
                        'RENEWED',
                        'DUE',
                        'CANCELLED',
                        'EXPIRED'
                    )
                ),
            auto_renew INTEGER NOT NULL
                CHECK (auto_renew IN (0, 1)),
            price REAL NOT NULL
                CHECK (price >= 0),
            currency TEXT NOT NULL
                CHECK (currency = 'EUR'),
            billing_frequency TEXT NOT NULL,

            FOREIGN KEY (member_id)
                REFERENCES members(member_id),

            CHECK (
                end_date IS NULL
                OR end_date >= start_date
            )
        );


        CREATE TABLE IF NOT EXISTS membership_events (
            event_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            event_type TEXT NOT NULL
                CHECK (
                    event_type IN (
                        'JOINED',
                        'RENEWED',
                        'UPGRADED',
                        'DOWNGRADED',
                        'SUSPENDED',
                        'REACTIVATED',
                        'CANCELLED'
                    )
                ),
            event_timestamp TEXT NOT NULL,
            previous_tier TEXT,
            new_tier TEXT,
            notes TEXT,

            FOREIGN KEY (member_id)
                REFERENCES members(member_id)
        );


        CREATE TABLE IF NOT EXISTS engagement_events (
            event_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            channel TEXT NOT NULL,

            FOREIGN KEY (member_id)
                REFERENCES members(member_id)
        );


        CREATE TABLE IF NOT EXISTS benefit_redemptions (
            redemption_id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL,
            benefit_code TEXT NOT NULL,
            redemption_timestamp TEXT NOT NULL,
            redemption_status TEXT NOT NULL
                CHECK (
                    redemption_status IN (
                        'REDEEMED',
                        'REVERSED',
                        'FAILED'
                    )
                ),
            monetary_value REAL
                CHECK (
                    monetary_value IS NULL
                    OR monetary_value >= 0
                ),

            FOREIGN KEY (member_id)
                REFERENCES members(member_id)
        );


        CREATE TABLE IF NOT EXISTS campaign_interactions (
            interaction_id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            member_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            sent_timestamp TEXT NOT NULL,
            response_type TEXT
                CHECK (
                    response_type IS NULL
                    OR response_type IN (
                        'OPENED',
                        'CLICKED',
                        'CONVERTED',
                        'IGNORED'
                    )
                ),
            response_timestamp TEXT,

            FOREIGN KEY (member_id)
                REFERENCES members(member_id)
        );


        CREATE INDEX IF NOT EXISTS idx_members_customer_id
            ON members(customer_id);

        CREATE INDEX IF NOT EXISTS idx_members_status
            ON members(membership_status);

        CREATE INDEX IF NOT EXISTS idx_members_tier
            ON members(membership_tier);


        CREATE INDEX IF NOT EXISTS idx_subscriptions_member_id
            ON subscriptions(member_id);

        CREATE INDEX IF NOT EXISTS idx_subscriptions_renewal_status
            ON subscriptions(renewal_status);


        CREATE INDEX IF NOT EXISTS idx_membership_events_member_id
            ON membership_events(member_id);

        CREATE INDEX IF NOT EXISTS idx_membership_events_timestamp
            ON membership_events(event_timestamp);


        CREATE INDEX IF NOT EXISTS idx_engagement_events_member_id
            ON engagement_events(member_id);

        CREATE INDEX IF NOT EXISTS idx_engagement_events_timestamp
            ON engagement_events(event_timestamp);


        CREATE INDEX IF NOT EXISTS idx_benefit_redemptions_member_id
            ON benefit_redemptions(member_id);

        CREATE INDEX IF NOT EXISTS idx_benefit_redemptions_timestamp
            ON benefit_redemptions(redemption_timestamp);


        CREATE INDEX IF NOT EXISTS idx_campaign_interactions_member_id
            ON campaign_interactions(member_id);

        CREATE INDEX IF NOT EXISTS idx_campaign_interactions_campaign_id
            ON campaign_interactions(campaign_id);
        """
    )

    connection.commit()


def validate_existing_customer_table(
    connection: sqlite3.Connection,
) -> None:
    """
    Membership data depends on the existing customers table.
    Fail early if the NBA database has not been built.
    """
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'customers'
        """
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "customers table not found. "
            "Run: python -m src.load_customers_to_sqlite"
        )


def verify_membership_schema(
    connection: sqlite3.Connection,
) -> None:
    existing_tables = {
        row[0]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
    }

    missing_tables = set(MEMBERSHIP_TABLES) - existing_tables

    if missing_tables:
        raise RuntimeError(
            "Membership schema verification failed. "
            f"Missing tables: {sorted(missing_tables)}"
        )

    foreign_keys_enabled = connection.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    if foreign_keys_enabled != 1:
        raise RuntimeError(
            "SQLite foreign-key enforcement is not enabled."
        )


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. "
            "Run: python -m src.load_customers_to_sqlite"
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        validate_existing_customer_table(connection)

        create_membership_schema(connection)

        verify_membership_schema(connection)

        customer_count = connection.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]

        table_counts = {}

        for table_name in MEMBERSHIP_TABLES:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            table_counts[table_name] = count

    print("=" * 70)
    print("NBA DECISIONING LAB - MEMBERSHIP SCHEMA")
    print("=" * 70)

    print(f"Database  : {DB_PATH}")
    print(f"Customers : {customer_count:,}")

    print()
    print("Membership tables:")

    for table_name, count in table_counts.items():
        print(
            f"  {table_name:<25} "
            f"{count:>10,} rows"
        )

    print()
    print("Foreign keys : ENABLED")
    print("VALIDATION   : PASS")


if __name__ == "__main__":
    main()