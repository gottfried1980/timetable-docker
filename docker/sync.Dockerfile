FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --gid 1000 timetable && useradd --uid 1000 --gid 1000 --no-create-home timetable
COPY requirements-sync.txt ./
RUN pip install --no-cache-dir -r requirements-sync.txt
COPY timetree_sync.py secret_crypto.py ./
COPY docker/sync_loop.py ./
USER timetable
CMD ["python", "/app/sync_loop.py"]
