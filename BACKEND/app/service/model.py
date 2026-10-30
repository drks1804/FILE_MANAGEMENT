from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from tokenizers import Tokenizer


MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANKER_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"
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
