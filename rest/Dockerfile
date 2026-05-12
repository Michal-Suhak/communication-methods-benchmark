FROM python:3.12-slim
WORKDIR /app
COPY rest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rest/ .
COPY shared/ /app/shared/
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
