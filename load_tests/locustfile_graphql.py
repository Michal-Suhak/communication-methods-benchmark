from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from locust import HttpUser, between, task

from shared.data_generator import generate_small_message


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

    @task(1)
    def get_large_full(self):
        self.client.post(
            "/graphql",
            json={"query": self._QUERY_FULL, "variables": {"sizeKb": 50}},
            name="query:getLarge[full]",
        )

    @task(1)
    def get_large_partial(self):
        self.client.post(
            "/graphql",
            json={"query": self._QUERY_PARTIAL, "variables": {"sizeKb": 50}},
            name="query:getLarge[partial]",
        )
