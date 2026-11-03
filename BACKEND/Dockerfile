FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy dependency list
COPY requirements.txt .

# Install CPU-only PyTorch and TorchVision
RUN pip install --no-cache-dir \
    --index-url https://pypi.org/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch==2.10.0+cpu" \
    "torchvision==0.25.0+cpu"

# Install remaining backend dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify CPU-only installation
RUN python -c "import torch, torchvision; print('PyTorch:', torch.__version__); print('TorchVision:', torchvision.__version__); print('CUDA available:', torch.cuda.is_available())"

# Copy application files
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Model cache location
ENV MODEL_CACHE_DIR=/models_cache \
    HF_HOME=/models_cache/hf

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
