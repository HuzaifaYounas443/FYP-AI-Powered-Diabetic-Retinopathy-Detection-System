FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5000

WORKDIR /app

# OpenCV needs these runtime libraries in a slim Debian image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install -r requirements.txt \
    && pip install gunicorn

COPY app.py ./
COPY utils ./utils
COPY templates ./templates
COPY static ./static
COPY models ./models

# Runtime directories are mounted by docker-compose in normal deployments.
RUN mkdir -p instance uploads static/generated/gradcam static/generated/reports

EXPOSE 5000

# One worker avoids loading two copies of the PyTorch models by default.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-1} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} app:app"]
