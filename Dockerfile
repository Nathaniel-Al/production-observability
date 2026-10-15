FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PORT=10000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 10000
# One worker on purpose: counter and log buffer live in process memory.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
