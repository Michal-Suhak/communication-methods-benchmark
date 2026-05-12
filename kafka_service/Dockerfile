FROM python:3.12-slim
WORKDIR /app
COPY kafka_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY kafka_service/ .
COPY shared/ /app/shared/
CMD ["python", "consumer.py"]
