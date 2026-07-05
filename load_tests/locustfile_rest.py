from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from locust import HttpUser, between, task

from shared.data_generator import (
    LARGE_PAYLOAD_BASE_KB,
    LARGE_PAYLOAD_EXTENDED_KB,
    generate_small_message,
)


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

    def _get_large(self, size_kb: int):
        url = f"/api/large?size_kb={size_kb}"
        self.client.post(url, name=url)

    @task
    def get_large_base(self):
        self._get_large(LARGE_PAYLOAD_BASE_KB)

    @task
    def get_large_extended(self):
        self._get_large(LARGE_PAYLOAD_EXTENDED_KB)
