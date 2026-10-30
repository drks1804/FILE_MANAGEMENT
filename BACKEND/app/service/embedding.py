from app.service.model import model
import numpy as np
import faiss


def generate_embeddings(
        chunks:list[str],
) -> np.ndarray:

    if not chunks:
        return np.empty((0,384), dtype="float32")
    
    embeddings = list(model.embed(chunks))

    embeddings = np.asarray(
        embeddings,
        dtype="float32"
    )

    faiss.normalize_L2(embeddings)

    return np.asarray(embeddings,dtype="float32")

def search_embeddings(search_query:str)->np.ndarray:

    query = (
        "Represent this sentence for searching relevant passages: "
        + search_query
    )

    embeddings = list(
        model.query_embed([query])
    )

    return np.asarray(embeddings,dtype="float32")
