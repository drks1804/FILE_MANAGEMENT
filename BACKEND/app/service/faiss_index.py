import faiss
import numpy as np
from pathlib import Path
from threading import Lock
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from app.service.s3_client import s3, BUCKET_NAME

load_dotenv()

S3_BUCKET = BUCKET_NAME
S3_KEY = "faiss/index.faiss"

embedding_dimension = 384

base_index = faiss.IndexFlatIP(embedding_dimension)

index = faiss.IndexIDMap2(base_index)

FAISS_index_path = Path("storage/faiss/index.faiss")

faiss_lock = Lock()


def write_local():
    FAISS_index_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = FAISS_index_path.with_suffix(".tmp")

    faiss.write_index(index, str(tmp_path))

    os.replace(tmp_path, FAISS_index_path)


def save_index():
    write_local()

    s3.upload_file(
        str(FAISS_index_path),
        S3_BUCKET,
        S3_KEY
    )


def add_embeddings_and_save(
    embeddings: np.ndarray,
    vector_ids: np.ndarray
) -> None:

    if embeddings.size == 0:
        return

    embeddings = embeddings.astype("float32")
    vector_ids = vector_ids.astype("int64")

    with faiss_lock:

        index.add_with_ids(
            embeddings,
            vector_ids
        )

        try:
            save_index()

        except Exception:
            index.remove_ids(vector_ids)

            try:
                write_local()
            except Exception:
                pass

            raise


def load_index() -> None:
    global index

    with faiss_lock:

        FAISS_index_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            s3.download_file(
                S3_BUCKET,
                S3_KEY,
                str(FAISS_index_path)
            )

        except ClientError as e:

            code = e.response["Error"]["Code"]

            if code in ("404", "NoSuchKey"):
                print("No FAISS index in S3 yet, starting with an empty index")
                return

            raise

        index = faiss.read_index(str(FAISS_index_path))

    print(f"Total vectors in FAISS: {index.ntotal}")


def remove_embeddings(vector_ids: np.ndarray) -> None:

    vector_ids = vector_ids.astype("int64")

    with faiss_lock:

        index.remove_ids(vector_ids)

        save_index()


def search_index(
    query_embedding: np.ndarray,
    allowed_vector_ids,
    top_k: int = 20
):

    query_embedding = query_embedding.astype("float32")

    if not allowed_vector_ids:
        return (
            np.empty((1, 0), dtype="float32"),
            np.empty((1, 0), dtype="int64")
        )

    allowed_vector_ids = np.asarray(
        allowed_vector_ids,
        dtype="int64"
    )

    selector = faiss.IDSelectorBatch(allowed_vector_ids)

    search_params = faiss.SearchParameters()
    search_params.sel = selector

    with faiss_lock:

        distances, vector_ids = index.search(
            query_embedding,
            top_k,
            params=search_params
        )

    return distances, vector_ids
