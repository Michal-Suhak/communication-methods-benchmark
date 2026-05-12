FROM python:3.12-slim
WORKDIR /app
COPY grpc_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY grpc_service/ .
COPY shared/ /app/shared/
RUN mkdir -p generated && \
    python -m grpc_tools.protoc \
        -I./proto \
        --python_out=./generated \
        --grpc_python_out=./generated \
        --pyi_out=./generated \
        proto/benchmark.proto && \
    touch generated/__init__.py
CMD ["python", "server.py"]
