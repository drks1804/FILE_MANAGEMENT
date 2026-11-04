from sqlalchemy.orm import Session
from app.database.models import File, Vector
from app.service.embedding import search_embeddings
from app.service.faiss_index import search_index
from app.service.reranking import rerank_chunks


def semantic_search_handler(
    query: str,
    user_id: int,
    db: Session
):
    # Step 1: Get only vector IDs belonging to the user's indexed files
    user_vector_rows = (
        db.query(Vector.vector_id)
        .join(File, Vector.file_id == File.file_id)
        .filter(
            File.user_id == user_id,
            File.is_indexed.is_(True),
            File.deleted_at.is_(None)
        )
        .all()
    )

    if not user_vector_rows:
        return []

    user_vector_ids = []

    for row in user_vector_rows:
        user_vector_ids.append(row[0])

    # Step 2: Generate the query embedding
    query_embedding = search_embeddings(query)

    # Step 3: Search FAISS for at most 20 allowed vectors
    top_k = min(20, len(user_vector_ids))

    distances, vector_ids = search_index(
        query_embedding=query_embedding,
        allowed_vector_ids=user_vector_ids,
        top_k=top_k
    )

    # Step 4: Keep valid candidate vector IDs
    candidate_vector_ids = []

    for vector_id in vector_ids[0]:
        if vector_id != -1:
            candidate_vector_ids.append(int(vector_id))

    if not candidate_vector_ids:
        return []

    # Step 5: Fetch the candidate vector records from MySQL
    candidate_vector_rows = (
        db.query(Vector)
        .join(File, Vector.file_id == File.file_id)
        .filter(
            Vector.vector_id.in_(candidate_vector_ids),
            File.user_id == user_id,
            File.is_indexed == True
        )
        .all()
    )

    # Step 6: Restore FAISS candidate order
    vectors_by_id = {}

    for vector in candidate_vector_rows:
        vectors_by_id[vector.vector_id] = vector

    candidate_vectors = []

    for vector_id in candidate_vector_ids:
        vector = vectors_by_id.get(vector_id)

        if vector is not None:
            candidate_vectors.append(vector)

    if not candidate_vectors:
        return []

    # Step 7: Extract candidate chunk text
    candidate_chunks = []

    for vector in candidate_vectors:
        candidate_chunks.append(vector.chunk_text)

    print("\n========== RERANKING DEBUG ==========")
    print("SEARCH QUERY:", query)

    for i, chunk in enumerate(candidate_chunks):
        print(f"\nCHUNK {i + 1}:")
        print(chunk)

    print("====================================\n")

    # Step 8: Rerank candidate chunks
    scores = rerank_chunks(
        query=query,
        chunks=candidate_chunks
    )

    if scores:
        print(max(scores))

    if len(scores) != len(candidate_vectors):
        raise ValueError(
            "Reranker score count does not match candidate count"
        )

    # Step 9: Pair scores with their corresponding vector records
    score_threshold = -8.0
    ranked_vectors = []

    for score , vector in zip(scores, candidate_vectors):
        if score >= score_threshold:
            ranked_vectors.append((score,vector))

    ranked_vectors.sort(
        key=lambda item: item[0],
        reverse=True
    )

    # Step 10: Select up to five unique files
    unique_files = []
    seen_file_ids = set()

    for score, vector in ranked_vectors:
        if vector.file_id not in seen_file_ids:
            seen_file_ids.add(vector.file_id)
            unique_files.append((score, vector.file_id))

        if len(unique_files) == 5:
            break

    if not unique_files:
        return []

    # Step 11: Fetch details for the selected files
    top_file_ids = []

    for score, file_id in unique_files:
        top_file_ids.append(file_id)

    top_files = (
        db.query(File)
        .filter(
            File.file_id.in_(top_file_ids),
            File.user_id == user_id,
            File.is_indexed == True
        )
        .all()
    )

    # Step 12: Map file IDs to file records
    files_by_id = {}

    for file in top_files:
        files_by_id[file.file_id] = file

    # Step 13: Return results in reranker order
    ranked_files = []

    for score, file_id in unique_files:
        file = files_by_id.get(file_id)

        if file is not None:
            ranked_files.append({
                "file_id": file.file_id,
                "file_name": file.file_name,
                "score": score
            })

    return ranked_files