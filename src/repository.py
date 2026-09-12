from functools import lru_cache
from pathlib import Path
import pandas as pd

from .models import Customer


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "customers.csv"


@lru_cache(maxsize=1)
def load_customers() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"{DATA_FILE} not found. Run: python -m src.synthetic_data"
        )
    return pd.read_csv(DATA_FILE)


def get_customer(customer_id: str) -> Customer | None:
    df = load_customers()
    rows = df.loc[df["customer_id"] == customer_id]

    if rows.empty:
        return None

    row = rows.iloc[0].to_dict()
    return Customer(**row)
