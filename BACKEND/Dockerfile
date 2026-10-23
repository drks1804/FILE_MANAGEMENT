
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Copy the application code.
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Download the sentence-transformer model during image build.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/e5-small-v2', cache_folder='/opt/huggingface')"

# Tell the application where the downloaded model is stored.
ENV HF_HOME=/opt/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/opt/huggingface

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
