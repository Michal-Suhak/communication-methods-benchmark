from __future__ import annotations

import sys
import time
import uuid

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/grpc_service")
sys.path.insert(0, "/app/grpc_service/generated")

from locust import User, between, events, task

import grpc
import benchmark_pb2        # loaded from /app/grpc_service/generated via sys.path
import benchmark_pb2_grpc   # its internal "import benchmark_pb2" now hits sys.modules

from shared.data_generator import (
    LARGE_PAYLOAD_BASE_KB,
    LARGE_PAYLOAD_EXTENDED_KB,
    generate_small_message,
)

_DEFAULT_TARGET = "grpc-server:50051"


class GrpcUserBase(User):
    abstract = True

    def on_start(self):
        self._channel = grpc.insecure_channel(
            self.host or _DEFAULT_TARGET,
            options=[
                ("grpc.keepalive_time_ms", 60000),
                ("grpc.max_send_message_length", 10 * 1024 * 1024),
                ("grpc.max_receive_message_length", 10 * 1024 * 1024),
            ],
        )
        self._stub = benchmark_pb2_grpc.BenchmarkServiceStub(self._channel)

    def on_stop(self):
        channel = getattr(self, "_channel", None)
        if channel is not None:
            channel.close()

    def _fire(self, name: str, start: float, response_length: int, exc):
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="grpc",
            name=name,
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exc,
        )


class GrpcSmallUser(GrpcUserBase):
    wait_time = between(0.01, 0.05)

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
        response_length = 0
        try:
            response = self._stub.SendSmall(req)
            response_length = response.ByteSize()
        except Exception as e:
            exc = e
        self._fire("SendSmall", start, response_length, exc)

    @task(1)
    def echo(self):
        req = benchmark_pb2.EchoRequest(data=b"x" * 256)
        start = time.perf_counter()
        exc = None
        response_length = 0
        try:
            response = self._stub.Echo(req)
            response_length = response.ByteSize()
        except Exception as e:
            exc = e
        self._fire("Echo", start, response_length, exc)


class GrpcLargeUser(GrpcUserBase):
    wait_time = between(0.1, 0.5)

    def _get_large(self, size_kb: int):
        req = benchmark_pb2.LargeRequest(id=str(uuid.uuid4()), size_kb=size_kb)
        start = time.perf_counter()
        exc = None
        response_length = 0
        try:
            response = self._stub.GetLarge(req)
            response_length = response.ByteSize()
        except Exception as e:
            exc = e
        self._fire(f"GetLarge[{size_kb}kb]", start, response_length, exc)

    @task(1)
    def get_large_base(self):
        self._get_large(LARGE_PAYLOAD_BASE_KB)

    @task(1)
    def get_large_extended(self):
        self._get_large(LARGE_PAYLOAD_EXTENDED_KB)
