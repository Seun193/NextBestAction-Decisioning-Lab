import sqlite3

import src.repository as repository


def create_test_database(db_path):
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                age INTEGER,
                monthly_income REAL,
                savings_balance REAL,
                monthly_surplus REAL,
                has_mortgage INTEGER,
                has_credit_card INTEGER,
                investment_customer INTEGER,
                app_visits_30d INTEGER,
                marketing_consent INTEGER,
                investment_consent INTEGER,
                credit_score_band TEXT,
                preferred_channel TEXT
            )
            """
        )

        connection.execute(
            """
            INSERT INTO customers
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "TEST001",
                35,
                4500.00,
                12000.00,
                850.00,
                0,
                1,
                0,
                14,
                1,
                1,
                "HIGH",
                "MOBILE",
            ),
        )

        connection.executescript(
            """
            CREATE TABLE members (
                member_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL UNIQUE,
                membership_status TEXT NOT NULL,
                membership_tier TEXT NOT NULL,
                join_date TEXT NOT NULL,
                end_date TEXT
            );

            CREATE TABLE engagement_events (
                event_id TEXT PRIMARY KEY,
                member_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_timestamp TEXT NOT NULL,
                channel TEXT NOT NULL
            );

            CREATE TABLE benefit_redemptions (
                redemption_id TEXT PRIMARY KEY,
                member_id TEXT NOT NULL,
                benefit_code TEXT NOT NULL,
                redemption_timestamp TEXT NOT NULL,
                redemption_status TEXT NOT NULL,
                monetary_value REAL
            );

            CREATE TABLE campaign_interactions (
                interaction_id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                member_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                sent_timestamp TEXT NOT NULL,
                response_type TEXT,
                response_timestamp TEXT
            );
            """
        )

        connection.execute(
            """
            INSERT INTO members
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "M000001",
                "TEST001",
                "ACTIVE",
                "PLUS",
                "2026-01-01",
                None,
            ),
        )

        connection.executemany(
            """
            INSERT INTO engagement_events
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "E001",
                    "M000001",
                    "APP_SESSION",
                    "2026-08-23T09:00:00",
                    "APP",
                ),
                (
                    "E002",
                    "M000001",
                    "CONTENT_VIEW",
                    "2026-09-21T22:00:00",
                    "WEB",
                ),
                (
                    "E003",
                    "M000001",
                    "EMAIL_OPEN",
                    "2026-08-22T12:00:00",
                    "EMAIL",
                ),
            ],
        )

        connection.executemany(
            """
            INSERT INTO benefit_redemptions
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "B001",
                    "M000001",
                    "PARTNER_DISCOUNT",
                    "2026-09-01T10:00:00",
                    "REDEEMED",
                    15.00,
                ),
                (
                    "B002",
                    "M000001",
                    "DINING_CREDIT",
                    "2026-09-05T10:00:00",
                    "FAILED",
                    20.00,
                ),
                (
                    "B003",
                    "M000001",
                    "WELCOME_REWARD",
                    "2026-08-22T10:00:00",
                    "REDEEMED",
                    10.00,
                ),
            ],
        )

        connection.executemany(
            """
            INSERT INTO campaign_interactions
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "C001",
                    "MEMBER_NEWS",
                    "M000001",
                    "EMAIL",
                    "2026-08-23T08:00:00",
                    "OPENED",
                    "2026-08-23T09:00:00",
                ),
                (
                    "C002",
                    "PLUS_UPGRADE",
                    "M000001",
                    "APP",
                    "2026-09-20T12:00:00",
                    "CONVERTED",
                    "2026-09-20T13:00:00",
                ),
                (
                    "C003",
                    "BENEFIT_DISCOVERY",
                    "M000001",
                    "EMAIL",
                    "2026-08-22T08:00:00",
                    "CONVERTED",
                    "2026-08-22T09:00:00",
                ),
                (
                    "C004",
                    "MEMBER_NEWS",
                    "M000001",
                    "APP",
                    "2026-09-22T08:00:00",
                    "CONVERTED",
                    "2026-09-22T09:00:00",
                ),
            ],
        )

        connection.commit()


def test_get_customer_from_sqlite(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    customer = repository.get_customer(
        "TEST001"
    )

    assert customer is not None
    assert customer.customer_id == "TEST001"
    assert customer.age == 35
    assert customer.monthly_income == 4500.00
    assert customer.savings_balance == 12000.00
    assert customer.has_credit_card is True
    assert customer.has_mortgage is False
    assert customer.credit_score_band == "HIGH"
    assert customer.preferred_channel == "MOBILE"


def test_unknown_customer_returns_none(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    assert (
        repository.get_customer(
            "DOES_NOT_EXIST"
        )
        is None
    )


def test_membership_context_returns_member_attributes(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    context = repository.get_membership_context(
        "TEST001"
    )

    assert context is not None
    assert context.member_id == "M000001"
    assert context.membership_status == "ACTIVE"
    assert context.membership_tier == "PLUS"


def test_membership_context_calculates_tenure(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    context = repository.get_membership_context(
        "TEST001"
    )

    assert context is not None
    assert context.tenure_days == 263


def test_membership_context_uses_inclusive_30_day_window(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    context = repository.get_membership_context(
        "TEST001"
    )

    assert context is not None
    assert context.engagement_events_30d == 2
    assert (
        context.successful_benefit_redemptions_30d
        == 1
    )
    assert context.campaign_sends_30d == 2
    assert context.campaign_conversions_30d == 1


def test_membership_context_uses_latest_observable_campaign_response(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    context = repository.get_membership_context(
        "TEST001"
    )

    assert context is not None

    assert (
        context.latest_campaign_response
        == "CONVERTED"
    )


def test_non_member_has_no_membership_context(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "test_nba.db"

    create_test_database(db_path)

    monkeypatch.setattr(
        repository,
        "DB_FILE",
        db_path,
    )

    assert (
        repository.get_membership_context(
            "DOES_NOT_EXIST"
        )
        is None
    )