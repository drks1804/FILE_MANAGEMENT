FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencies first, so this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Models are not in the image. They download on first start into this folder,
# which docker-compose mounts as a volume. HF_HOME keeps the tokenizer there too.
ENV MODEL_CACHE_DIR=/models_cache \
    HF_HOME=/models_cache/hf

EXPOSE 8000

# One worker only: each extra worker loads its own copy of the models and the index
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]