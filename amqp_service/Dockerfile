FROM python:3.12-slim
WORKDIR /app
COPY amqp_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY amqp_service/ .
COPY shared/ /app/shared/
CMD ["python", "consumer.py"]
