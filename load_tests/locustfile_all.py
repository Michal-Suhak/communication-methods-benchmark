"""Smoke-test / interactive UI (--class-picker) ONLY.

Do NOT use for comparative measurements: running all User classes at once mixes
fire-and-forget publishes (AMQP/Kafka) with blocking round-trips (REST/gRPC) in
a single gevent process, which distorts round-trip latency through greenlet
contention. For measurements use the per-protocol locustfiles (run_all_scenarios.sh)."""
from locustfile_amqp import AMQPLargeUser, AMQPSmallUser
from locustfile_graphql import GraphQLLargeUser, GraphQLSmallUser
from locustfile_grpc import GrpcLargeUser, GrpcSmallUser
from locustfile_kafka import KafkaLargeUser, KafkaSmallUser
from locustfile_rest import RestLargeResponseUser, RestSmallMessageUser

__all__ = [
    "RestSmallMessageUser",
    "RestLargeResponseUser",
    "GrpcSmallUser",
    "GrpcLargeUser",
    "GraphQLSmallUser",
    "GraphQLLargeUser",
    "AMQPSmallUser",
    "AMQPLargeUser",
    "KafkaSmallUser",
    "KafkaLargeUser",
]
