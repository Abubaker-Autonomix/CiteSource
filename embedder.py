"""
Local, free embeddings using fastembed (ONNX-based, no torch required).
Much lighter than sentence-transformers+torch (~200-300MB total vs 1-2GB).
Model downloads once (~130MB) on first use, then runs on CPU.
"""
from fastembed import TextEmbedding

_model = None


def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]
