# syntax=docker/dockerfile:1
# FastAPI backend / simulation worker image.

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Default command runs the API. The worker service overrides this with
# `python -m app.worker`. Run migrations before the API in production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
