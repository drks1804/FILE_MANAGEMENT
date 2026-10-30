from app.service.model import tokenizer

def chunk_text(
        text:str,
        max_tokens: int = 300,
        token_overlap:int=50,
)->list[str]:

    if not text.strip():
        return []

    if token_overlap >= max_tokens:
        raise ValueError("token overlap cannot be more than max tokens")

    offsets=tokenizer.encode(
        text,add_special_tokens=False
    ).offsets

    n=len(offsets)

    chunks = []

    start = 0

    step = max_tokens - token_overlap

    while start < n:
        end = min(start + max_tokens,n)

        chunk = text[offsets[start][0]:offsets[end-1][1]].strip()

        if chunk:
            chunks.append(chunk)

        if end == n:
            break

        start += step
    return chunks    