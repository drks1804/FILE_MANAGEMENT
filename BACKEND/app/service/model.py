
import torch

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from tokenizers import Tokenizer
from transformers import AutoProcessor, AutoModelForMultimodalLM


MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANKER_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"
FLORENCE_MODEL_NAME = "florence-community/Florence-2-base-ft"

MODEL_CACHE_DIR = "models_cache"


# Embedding model
model = TextEmbedding(
    model_name=MODEL_NAME,
    cache_dir=MODEL_CACHE_DIR,
    threads=1
)


# Reranker model
reranker = TextCrossEncoder(
    model_name=RERANKER_NAME,
    cache_dir=MODEL_CACHE_DIR,
    threads=1
)


# Tokenizer for document chunking
tokenizer = Tokenizer.from_pretrained(MODEL_NAME)

tokenizer.no_truncation()
tokenizer.no_padding()


# Florence-2 processor
florence_processor = AutoProcessor.from_pretrained(
    FLORENCE_MODEL_NAME,
    cache_dir=MODEL_CACHE_DIR,
    local_files_only=True
)


# Florence-2 model
florence_model = AutoModelForMultimodalLM.from_pretrained(
    FLORENCE_MODEL_NAME,
    cache_dir=MODEL_CACHE_DIR,
    dtype=torch.float32,
    local_files_only=True
)

florence_model.to("cpu")
florence_model.eval()
