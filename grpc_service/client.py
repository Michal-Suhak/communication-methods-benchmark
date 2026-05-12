from __future__ import annotations

import asyncio
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import grpc

from generated import benchmark_pb2, benchmark_pb2_grpc
from shared.models import BenchmarkResult, SmallMessage

_TARGET = "grpc-server:50051"
_OPTIONS = [
    ("grpc.keepalive_time_ms", 60000),
    ("grpc.max_send_message_length", 10 * 1024 * 1024),
    ("grpc.max_receive_message_length", 10 * 1024 * 1024),
]


class GrpcBenchmarkClient:
    def __init__(self, target: str = _TARGET) -> None:
        self._channel = grpc.insecure_channel(target, options=_OPTIONS)
        self._stub = benchmark_pb2_grpc.BenchmarkServiceStub(self._channel)

    def close(self):
        self._channel.close()

    def send_small(self, msg: SmallMessage) -> BenchmarkResult:
        req = benchmark_pb2.SmallRequest(
            id=msg.id,
            timestamp=msg.timestamp,
            source=msg.source,
            payload=msg.payload,
        )
        payload_size = req.ByteSize()
        start = time.perf_counter()
        try:
            self._stub.SendSmall(req)
            success = True
        except grpc.RpcError:
            success = False
        elapsed_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            method="grpc",
            scenario="small",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=success,
            payload_size_bytes=payload_size,
        )

    def request_large(self, size_kb: int = 50) -> BenchmarkResult:
        req = benchmark_pb2.LargeRequest(id=str(uuid.uuid4()), size_kb=size_kb)
        start = time.perf_counter()
        try:
            response = self._stub.GetLarge(req)
            payload_size = response.ByteSize()
            success = True
        except grpc.RpcError:
            payload_size = 0
            success = False
        elapsed_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            method="grpc",
            scenario="large",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=success,
            payload_size_bytes=payload_size,
        )

    def echo(self, data: bytes) -> BenchmarkResult:
        req = benchmark_pb2.EchoRequest(data=data)
        start = time.perf_counter()
        try:
            self._stub.Echo(req)
            success = True
        except grpc.RpcError:
            success = False
        elapsed_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            method="grpc",
            scenario="echo",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=success,
            payload_size_bytes=len(data),
        )

    def stream_large(self, size_kb: int = 50) -> BenchmarkResult:
        req = benchmark_pb2.LargeRequest(id=str(uuid.uuid4()), size_kb=size_kb)
        start = time.perf_counter()
        try:
            total_bytes = sum(item.ByteSize() for item in self._stub.StreamLarge(req))
            success = True
        except grpc.RpcError:
            total_bytes = 0
            success = False
        elapsed_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            method="grpc",
            scenario="stream_large",
            latency_ms=elapsed_ms,
            timestamp=time.time(),
            success=success,
            payload_size_bytes=total_bytes,
        )
