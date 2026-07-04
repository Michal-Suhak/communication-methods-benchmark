"""TYLKO smoke-test / interaktywne UI (--class-picker).

NIE używać do pomiarów porównawczych: uruchomienie wszystkich klas User naraz
miesza fire-and-forget/publish (AMQP/Kafka) z blokującymi round-tripami (REST/gRPC)
w jednym procesie gevent, co zaburza latencję protokołów round-trip przez rywalizację
o greenlety. Do pomiarów używaj pojedynczych locustfile'ów (run_all_scenarios.sh)."""
from locustfile_amqp import AMQPUser
from locustfile_graphql import GraphQLLargeUser, GraphQLSmallUser
from locustfile_grpc import GrpcUser
from locustfile_kafka import KafkaUser
from locustfile_rest import RestLargeResponseUser, RestSmallMessageUser

__all__ = [
    "RestSmallMessageUser",
    "RestLargeResponseUser",
    "GrpcUser",
    "GraphQLSmallUser",
    "GraphQLLargeUser",
    "AMQPUser",
    "KafkaUser",
]