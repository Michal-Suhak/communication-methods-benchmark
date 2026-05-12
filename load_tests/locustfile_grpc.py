from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/grpc_service")
sys.path.insert(0, "/app/grpc_service/generated")

from locust import User, between, events, task

import grpc
import benchmark_pb2        # loaded from /app/grpc_service/generated via sys.path
import benchmark_pb2_grpc   # its internal "import benchmark_pb2" now hits sys.modules

from shared.data_generator import generate_small_message

_TARGET = "grpc-server:50051"


class GrpcUser(User):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self._channel = grpc.insecure_channel(
            _TARGET,
            options=[
                ("grpc.keepalive_time_ms", 60000),
                ("grpc.max_send_message_length", 10 * 1024 * 1024),
                ("grpc.max_receive_message_length", 10 * 1024 * 1024),
            ],
        )
        self._stub = benchmark_pb2_grpc.BenchmarkServiceStub(self._channel)

    def on_stop(self):
        self._channel.close()

    @task(3)
    def send_small(self):
        msg = generate_small_message()
        req = benchmark_pb2.SmallRequest(
            id=msg.id,
            timestamp=msg.timestamp,
            source=msg.source,
            payload=msg.payload,
        )
        start = time.perf_counter()
        exc = None
        try:
            self._stub.SendSmall(req)
        except grpc.RpcError as e:
            exc = e
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="grpc",
            name="SendSmall",
            response_time=elapsed_ms,
            response_length=0,
            exception=exc,
        )

    @task(1)
    def get_large(self):
        req = benchmark_pb2.LargeRequest(id=str(uuid.uuid4()), size_kb=50)
        start = time.perf_counter()
        exc = None
        response_length = 0
        try:
            response = self._stub.GetLarge(req)
            response_length = response.ByteSize()
        except grpc.RpcError as e:
            exc = e
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="grpc",
            name="GetLarge",
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exc,
        )
