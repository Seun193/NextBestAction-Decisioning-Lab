from pathlib import Path
import sqlite3

from .models import Customer


DB_FILE = Path(__file__).resolve().parents[1] / "data" / "nba_lab.db"


def get_connection() -> sqlite3.Connection:
    """
    Open a connection to the NBA Decisioning Lab SQLite database.
    """
    if not DB_FILE.exists():
        raise FileNotFoundError(
            f"{DB_FILE} not found. "
            "Run: python -m src.load_customers_to_sqlite"
        )

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def get_customer(customer_id: str) -> Customer | None:
    """
    Retrieve one customer from SQLite by customer_id.
    """
    sql = """
        SELECT
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
        FROM customers
        WHERE customer_id = ?
    """

    with get_connection() as connection:
        row = connection.execute(sql, (customer_id,)).fetchone()

    if row is None:
        return None

    return Customer(**dict(row))
