from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from locust import HttpUser, between, events, task

from shared.data_generator import generate_large_message, generate_small_message


class RestSmallMessageUser(HttpUser):
    host = "http://rest-server:8001"
    wait_time = between(0.01, 0.05)

    @task(3)
    def send_small(self):
        msg = generate_small_message()
        payload = msg.model_dump_json()
        self.client.post(
            "/api/small",
            data=payload,
            headers={"content-type": "application/json"},
            name="/api/small",
        )

    @task(1)
    def echo(self):
        data = b"x" * 256
        self.client.post("/api/echo", data=data, name="/api/echo")


class RestLargeResponseUser(HttpUser):
    host = "http://rest-server:8001"
    wait_time = between(0.1, 0.5)

    @task
    def get_large_50kb(self):
        self.client.post("/api/large?size_kb=50", name="/api/large?size_kb=50")

    @task
    def get_large_100kb(self):
        self.client.post("/api/large?size_kb=100", name="/api/large?size_kb=100")
