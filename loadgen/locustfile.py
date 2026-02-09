import random
from locust import HttpUser, task, between


class OrderUser(HttpUser):
    """
    Simulates users creating orders through the API.

    The wait time between tasks can be configured to simulate
    different traffic patterns.
    """

    # Wait between 1 and 3 seconds between tasks
    wait_time = between(1, 3)

    @task(10)
    def create_order(self):
        """
        Creates a new order via POST /orders.

        Weight: 10 (most common operation)
        """
        products = [
            "Widget Pro",
            "Gadget Ultra",
            "ThingaMajig",
            "Doohickey 3000",
            "Whatsit Premium",
        ]

        order = {
            "product": random.choice(products),
            "quantity": random.randint(1, 10),
            "customerName": f"LoadTest-User-{random.randint(1000, 9999)}",
        }

        with self.client.post(
            "/orders",
            json=order,
            catch_response=True,
            name="POST /orders"
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(3)
    def list_orders(self):
        """
        Lists all orders via GET /orders.

        Weight: 3 (less common than creating)
        """
        with self.client.get(
            "/orders",
            catch_response=True,
            name="GET /orders"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(1)
    def get_order_detail(self):
        """
        Gets a specific order detail via GET /orders/{id}.

        Weight: 1 (least common operation)
        Note: This may fail if the order doesn't exist, which is expected in load testing.
        """
        # Try a random order ID (some will fail with 404, which is fine)
        order_id = random.randint(1, 100)

        with self.client.get(
            f"/orders/{order_id}",
            catch_response=True,
            name="GET /orders/{id}"
        ) as response:
            if response.status_code in (200, 404):
                # Both success and not found are acceptable
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
