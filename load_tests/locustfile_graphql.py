from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from locust import HttpUser, between, task

from shared.data_generator import (
    LARGE_PAYLOAD_BASE_KB,
    LARGE_PAYLOAD_EXTENDED_KB,
    generate_small_message,
)


class GraphQLSmallUser(HttpUser):
    host = "http://graphql-server:8003"
    wait_time = between(0.01, 0.05)

    _MUTATION = """
    mutation($id: String!, $timestamp: Float!, $source: String!, $payload: String!) {
        sendSmall(id: $id, timestamp: $timestamp, source: $source, payload: $payload)
    }
    """

    @task(3)
    def send_small(self):
        msg = generate_small_message()
        self.client.post(
            "/graphql",
            json={
                "query": self._MUTATION,
                "variables": {
                    "id": msg.id,
                    "timestamp": msg.timestamp,
                    "source": msg.source,
                    "payload": msg.payload,
                },
            },
            name="mutation:sendSmall",
        )

    @task(1)
    def echo(self):
        self.client.post(
            "/graphql",
            json={"query": 'mutation { echo(data: "benchmark-echo-payload") }'},
            name="mutation:echo",
        )


class GraphQLLargeUser(HttpUser):
    host = "http://graphql-server:8003"
    wait_time = between(0.1, 0.5)

    _QUERY_FULL = """
    query($sizeKb: Int!) {
        getLarge(sizeKb: $sizeKb) { id timestamp items { name description value tags } }
    }
    """
    _QUERY_PARTIAL = """
    query($sizeKb: Int!) {
        getLarge(sizeKb: $sizeKb) { id items { name value } }
    }
    """

    def _get_large(self, query: str, variant: str, size_kb: int):
        self.client.post(
            "/graphql",
            json={"query": query, "variables": {"sizeKb": size_kb}},
            name=f"query:getLarge[{variant},{size_kb}kb]",
        )

    @task(1)
    def get_large_full_base(self):
        self._get_large(self._QUERY_FULL, "full", LARGE_PAYLOAD_BASE_KB)

    @task(1)
    def get_large_full_extended(self):
        self._get_large(self._QUERY_FULL, "full", LARGE_PAYLOAD_EXTENDED_KB)

    @task(1)
    def get_large_partial_base(self):
        self._get_large(self._QUERY_PARTIAL, "partial", LARGE_PAYLOAD_BASE_KB)

    @task(1)
    def get_large_partial_extended(self):
        self._get_large(self._QUERY_PARTIAL, "partial", LARGE_PAYLOAD_EXTENDED_KB)
