import random

from locust import HttpUser, between, task


MIN_CUSTOMER_ID = 1
MAX_CUSTOMER_ID = 20_000


class NBAUser(HttpUser):
    """
    Simulated user requesting Next Best Action decisions.

    Each user:
    - selects a valid synthetic customer
    - calls the NBA endpoint
    - validates critical response-contract fields
    - waits approximately one second
    - repeats
    """

    wait_time = between(0.8, 1.2)

    @task
    def get_next_best_action(self):
        customer_number = random.randint(
            MIN_CUSTOMER_ID,
            MAX_CUSTOMER_ID,
        )

        customer_id = f"C{customer_number:05d}"

        with self.client.get(
            f"/nba/{customer_id}",
            name="/nba/[customer_id]",
            catch_response=True,
        ) as response:

            if response.status_code != 200:
                response.failure(
                    f"Unexpected HTTP status "
                    f"{response.status_code}"
                )
                return

            try:
                payload = response.json()
            except ValueError:
                response.failure("Response was not valid JSON")
                return

            required_fields = {
                "customer_id",
                "next_best_action",
                "score",
                "eligible",
                "reason_codes",
                "ranked_actions",
            }

            missing_fields = required_fields - payload.keys()

            if missing_fields:
                response.failure(
                    "Missing response fields: "
                    + ", ".join(sorted(missing_fields))
                )
                return

            if payload["customer_id"] != customer_id:
                response.failure(
                    f"Customer mismatch: requested {customer_id}, "
                    f"received {payload['customer_id']}"
                )
                return

            if not isinstance(payload["next_best_action"], str):
                response.failure(
                    "next_best_action was not a string"
                )
                return

            if not isinstance(payload["eligible"], bool):
                response.failure(
                    "eligible was not a boolean"
                )
                return

            if not isinstance(payload["reason_codes"], list):
                response.failure(
                    "reason_codes was not a list"
                )
                return

            if not isinstance(payload["ranked_actions"], list):
                response.failure(
                    "ranked_actions was not a list"
                )
                return

            if not payload["ranked_actions"]:
                response.failure(
                    "ranked_actions was unexpectedly empty"
                )
                return

            response.success()