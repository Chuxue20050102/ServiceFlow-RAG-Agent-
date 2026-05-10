import json
from pathlib import Path

import faiss
import numpy as np

from app.core.config import get_settings
from app.models.serviceflow import KnowledgeChunk
from app.services.ai_client import create_embeddings


def add_rule_chunks_to_vector_store(chunks: list[KnowledgeChunk]) -> None:
    if not chunks:
        return

    texts = [chunk.content for chunk in chunks]
    embeddings = create_embeddings(texts)
    vectors = to_numpy_vectors(embeddings)

    index, metadata = load_index(vectors.shape[1])
    index.add(vectors)

    for chunk in chunks:
        metadata.append(
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
            }
        )

    save_index(index, metadata)


def search_rule_chunks(query: str, limit: int = 3) -> list[str]:
    paths = get_vector_paths()
    if not paths["index"].exists() or not paths["metadata"].exists():
        return []

    index = faiss.read_index(str(paths["index"]))
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))

    query_vector = to_numpy_vectors(create_embeddings([query]))
    _, indexes = index.search(query_vector, limit)

    results: list[str] = []
    for position in indexes[0]:
        if position == -1:
            continue
        if position < len(metadata):
            results.append(metadata[position]["content"])

    return results


def load_index(dimension: int):
    paths = get_vector_paths()
    if paths["index"].exists():
        index = faiss.read_index(str(paths["index"]))
    else:
        index = faiss.IndexFlatIP(dimension)

    if paths["metadata"].exists():
        metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    else:
        metadata = []

    return index, metadata


def save_index(index, metadata: list[dict]) -> None:
    paths = get_vector_paths()
    paths["dir"].mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(paths["index"]))
    paths["metadata"].write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def to_numpy_vectors(embeddings: list[list[float]]) -> np.ndarray:
    vectors = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(vectors)
    return vectors


def get_vector_paths() -> dict[str, Path]:
    settings = get_settings()
    store_dir = Path(settings.vector_store_dir)
    return {
        "dir": store_dir,
        "index": store_dir / "rules.faiss",
        "metadata": store_dir / "rules_metadata.json",
    }

