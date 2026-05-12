FROM python:3.12-slim
WORKDIR /app
COPY load_tests/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY load_tests/ .
COPY shared/ /app/shared/
COPY grpc_service/ /app/grpc_service/
# Generate gRPC stubs inside the image
RUN mkdir -p /app/grpc_service/generated && \
    python -m grpc_tools.protoc \
        -I/app/grpc_service/proto \
        --python_out=/app/grpc_service/generated \
        --grpc_python_out=/app/grpc_service/generated \
        /app/grpc_service/proto/benchmark.proto && \
    touch /app/grpc_service/generated/__init__.py /app/grpc_service/__init__.py
CMD ["locust", "-f", "locustfile_rest.py", "--host", "http://rest-server:8001"]
