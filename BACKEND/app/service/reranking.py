from app.service.model import reranker

def rerank_chunks(
    query:str,
    chunks:list[str]
):

    scores = reranker.rerank(
        query=query,
        documents=chunks
    )

    return list(scores)