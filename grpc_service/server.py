from __future__ import annotations

import sys
import time
import uuid
from concurrent import futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "generated"))

import grpc
from grpc_reflection.v1alpha import reflection

from generated import benchmark_pb2, benchmark_pb2_grpc
from shared.data_generator import generate_large_message
from shared.metrics import (
    MESSAGE_SIZE,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    start_metrics_server,
)


class BenchmarkServicer(benchmark_pb2_grpc.BenchmarkServiceServicer):
    def SendSmall(self, request, context):
        start = time.perf_counter()
        response = benchmark_pb2.SmallResponse(
            id=request.id,
            success=True,
            server_timestamp=time.time(),
        )
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(method="grpc", scenario="small").observe(elapsed)
        REQUEST_COUNT.labels(method="grpc", scenario="small", status="success").inc()
        MESSAGE_SIZE.labels(method="grpc", scenario="small").observe(request.ByteSize())
        return response

    def GetLarge(self, request, context):
        start = time.perf_counter()
        large = generate_large_message(request.size_kb or 50)
        items = [
            benchmark_pb2.Item(
                name=item.name,
                description=item.description,
                value=item.value,
                tags=item.tags,
                metadata=item.metadata,
            )
            for item in large.items
        ]
        response = benchmark_pb2.LargeResponse(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            items=items,
        )
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(method="grpc", scenario="large").observe(elapsed)
        REQUEST_COUNT.labels(method="grpc", scenario="large", status="success").inc()
        MESSAGE_SIZE.labels(method="grpc", scenario="large").observe(response.ByteSize())
        return response

    def Echo(self, request, context):
        start = time.perf_counter()
        response = benchmark_pb2.EchoResponse(data=request.data)
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(method="grpc", scenario="echo").observe(elapsed)
        REQUEST_COUNT.labels(method="grpc", scenario="echo", status="success").inc()
        return response

    def StreamLarge(self, request, context):
        large = generate_large_message(request.size_kb or 50)
        for item in large.items:
            yield benchmark_pb2.Item(
                name=item.name,
                description=item.description,
                value=item.value,
                tags=item.tags,
                metadata=item.metadata,
            )

    def StreamSmall(self, request_iterator, context):
        for request in request_iterator:
            yield benchmark_pb2.SmallResponse(
                id=request.id,
                success=True,
                server_timestamp=time.time(),
            )


def serve():
    start_metrics_server(9091)
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.keepalive_time_ms", 60000),
            ("grpc.max_send_message_length", 10 * 1024 * 1024),
            ("grpc.max_receive_message_length", 10 * 1024 * 1024),
        ],
    )
    benchmark_pb2_grpc.add_BenchmarkServiceServicer_to_server(BenchmarkServicer(), server)

    service_names = (
        benchmark_pb2.DESCRIPTOR.services_by_name["BenchmarkService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server listening on :50051", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
