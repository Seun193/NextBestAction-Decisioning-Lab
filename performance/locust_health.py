from locust import HttpUser, between, task


class HealthUser(HttpUser):
    wait_time = between(0.8, 1.2)

    @task
    def health_check(self):
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True,
        ) as response:

            if response.status_code != 200:
                response.failure(
                    f"Unexpected HTTP status {response.status_code}"
                )
                return

            try:
                payload = response.json()
            except ValueError:
                response.failure("Response was not valid JSON")
                return

            if payload.get("status") != "ok":
                response.failure(
                    f"Unexpected health status: {payload}"
                )
                return

            if payload.get("version") != "1.0.0":
                response.failure(
                    f"Unexpected API version: {payload}"
                )
                return

            response.success()