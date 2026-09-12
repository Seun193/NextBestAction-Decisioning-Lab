from pathlib import Path
import numpy as np
import pandas as pd


SEED = 42
N_CUSTOMERS = 20_000

OUT = Path(__file__).resolve().parents[1] / "data" / "customers.csv"


def generate_customers(n: int = N_CUSTOMERS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = rng.integers(18, 76, size=n)
    monthly_income = np.clip(rng.normal(3800, 1500, size=n), 900, 14000)
    savings_balance = np.clip(
        rng.lognormal(mean=8.4, sigma=1.1, size=n) - 3500,
        0,
        250000,
    )
    monthly_surplus = np.clip(
        monthly_income * rng.normal(0.16, 0.14, size=n),
        -1500,
        5000,
    )

    has_mortgage = rng.random(n) < np.clip((age - 24) / 65, 0.05, 0.65)
    has_credit_card = rng.random(n) < 0.72
    investment_customer = rng.random(n) < np.clip(
        0.10 + (monthly_income - 2000) / 20000 + savings_balance / 500000,
        0.08,
        0.65,
    )

    app_visits_30d = np.clip(rng.poisson(8, size=n), 0, 50)
    marketing_consent = rng.random(n) < 0.84
    investment_consent = rng.random(n) < 0.68

    credit_score_band = rng.choice(
        ["LOW", "MEDIUM", "HIGH"],
        size=n,
        p=[0.12, 0.48, 0.40],
    )

    preferred_channel = rng.choice(
        ["MOBILE", "WEB", "BRANCH", "PHONE"],
        size=n,
        p=[0.58, 0.24, 0.10, 0.08],
    )

    df = pd.DataFrame(
        {
            "customer_id": [f"C{i:05d}" for i in range(1, n + 1)],
            "age": age,
            "monthly_income": monthly_income.round(2),
            "savings_balance": savings_balance.round(2),
            "monthly_surplus": monthly_surplus.round(2),
            "has_mortgage": has_mortgage,
            "has_credit_card": has_credit_card,
            "investment_customer": investment_customer,
            "app_visits_30d": app_visits_30d,
            "marketing_consent": marketing_consent,
            "investment_consent": investment_consent,
            "credit_score_band": credit_score_band,
            "preferred_channel": preferred_channel,
        }
    )

    return df


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = generate_customers()
    df.to_csv(OUT, index=False)
    print(f"Created {len(df):,} synthetic customers")
    print(f"Saved to: {OUT}")


if __name__ == "__main__":
    main()
