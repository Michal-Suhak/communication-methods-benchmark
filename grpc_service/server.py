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
    canonical_scenario,
    start_metrics_server,
)


class MetricsInterceptor(grpc.ServerInterceptor):
    """Mierzy pełny czas obsługi RPC (cały handler, włącznie ze streamingiem),
    zamiast mikrosekundowej konstrukcji obiektu odpowiedzi. Dzięki temu zakres
    pomiaru jest spójny z middleware REST (pełna obsługa po stronie serwera)."""

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None:
            return handler
        method = handler_call_details.method.split("/")[-1]
        scenario = canonical_scenario(method)

        if handler.unary_unary:
            behavior, factory, resp_stream = (
                handler.unary_unary,
                grpc.unary_unary_rpc_method_handler,
                False,
            )
        elif handler.unary_stream:
            behavior, factory, resp_stream = (
                handler.unary_stream,
                grpc.unary_stream_rpc_method_handler,
                True,
            )
        elif handler.stream_unary:
            behavior, factory, resp_stream = (
                handler.stream_unary,
                grpc.stream_unary_rpc_method_handler,
                False,
            )
        else:
            behavior, factory, resp_stream = (
                handler.stream_stream,
                grpc.stream_stream_rpc_method_handler,
                True,
            )

        def _record(start: float, status: str) -> None:
            REQUEST_LATENCY.labels(method="grpc", scenario=scenario).observe(
                time.perf_counter() - start
            )
            REQUEST_COUNT.labels(method="grpc", scenario=scenario, status=status).inc()

        def measured(request_or_iterator, context):
            start = time.perf_counter()
            try:
                result = behavior(request_or_iterator, context)
            except Exception:
                _record(start, "error")
                raise
            if resp_stream:
                def gen():
                    try:
                        for item in result:
                            yield item
                    except Exception:
                        _record(start, "error")
                        raise
                    else:
                        _record(start, "success")

                return gen()
            _record(start, "success")
            return result

        return factory(
            measured,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )


class BenchmarkServicer(benchmark_pb2_grpc.BenchmarkServiceServicer):
    def SendSmall(self, request, context):
        MESSAGE_SIZE.labels(method="grpc", scenario="small").observe(request.ByteSize())
        return benchmark_pb2.SmallResponse(
            id=request.id,
            success=True,
            server_timestamp=time.time(),
        )

    def GetLarge(self, request, context):
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
        MESSAGE_SIZE.labels(method="grpc", scenario="large").observe(response.ByteSize())
        return response

    def Echo(self, request, context):
        MESSAGE_SIZE.labels(method="grpc", scenario="echo").observe(request.ByteSize())
        return benchmark_pb2.EchoResponse(data=request.data)

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
        interceptors=[MetricsInterceptor()],
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
