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
            INSERT INTO customers (
                customer_id,
                age,
                monthly_income,
                savings_balance,
                monthly_surplus,
                has_mortgage,
                has_credit_card,
                investment_customer,
                app_visits_30d,
                marketing_consent,
                investment_consent,
                credit_score_band,
                preferred_channel
            )
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

        connection.commit()


def test_get_customer_from_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "test_nba.db"
    create_test_database(db_path)

    monkeypatch.setattr(repository, "DB_FILE", db_path)

    customer = repository.get_customer("TEST001")

    assert customer is not None
    assert customer.customer_id == "TEST001"
    assert customer.age == 35
    assert customer.monthly_income == 4500.00
    assert customer.savings_balance == 12000.00
    assert customer.has_credit_card is True
    assert customer.has_mortgage is False
    assert customer.credit_score_band == "HIGH"
    assert customer.preferred_channel == "MOBILE"


def test_unknown_customer_returns_none(tmp_path, monkeypatch):
    db_path = tmp_path / "test_nba.db"
    create_test_database(db_path)

    monkeypatch.setattr(repository, "DB_FILE", db_path)

    customer = repository.get_customer("DOES_NOT_EXIST")

    assert customer is None
