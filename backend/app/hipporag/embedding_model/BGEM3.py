from typing import List
import os

import numpy as np
import torch
from tqdm import tqdm

from .base import BaseEmbeddingModel
from ..utils.config_utils import BaseConfig
from ..utils.logging_utils import get_logger

logger = get_logger(__name__)


class BGEM3EmbeddingModel(BaseEmbeddingModel):
    """
    Dedicated embedding wrapper for BGE-M3.

    It prefers the official FlagEmbedding implementation when available and
    falls back to sentence-transformers dense embeddings otherwise.
    """

    def __init__(self, global_config: BaseConfig, embedding_model_name: str) -> None:
        super().__init__(global_config=global_config)

        if embedding_model_name.startswith("Transformers/"):
            self.model_id = embedding_model_name[len("Transformers/"):]
        else:
            self.model_id = embedding_model_name
        self.batch_size = self.global_config.embedding_batch_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_length = self.global_config.embedding_max_seq_len

        self.backend, self.model = self._load_model()

    def _load_model(self):
        prefer_flagembedding = os.getenv("HIPPORAG_BGE_BACKEND", "").lower() == "flagembedding"
        sentence_transformers_error = None
        flagembedding_error = None

        if not prefer_flagembedding:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading BGE-M3 with sentence-transformers backend.")
                return "sentence-transformers", SentenceTransformer(self.model_id, device=self.device)
            except Exception as exc:
                sentence_transformers_error = exc
                logger.warning(f"Falling back from sentence-transformers to FlagEmbedding: {exc}")

        try:
            from FlagEmbedding import BGEM3FlagModel

            logger.info("Loading BGE-M3 with FlagEmbedding backend.")
            return "flagembedding", BGEM3FlagModel(
                self.model_id,
                use_fp16=torch.cuda.is_available(),
            )
        except Exception as exc:
            flagembedding_error = exc

        if prefer_flagembedding:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("FlagEmbedding backend unavailable; falling back to sentence-transformers backend.")
                return "sentence-transformers", SentenceTransformer(self.model_id, device=self.device)
            except Exception as exc:
                sentence_transformers_error = exc

        raise RuntimeError(
            f"Failed to load BGE-M3 with either sentence-transformers or FlagEmbedding. "
            f"sentence-transformers error: {sentence_transformers_error!r}; "
            f"FlagEmbedding error: {flagembedding_error!r}"
        )

    def _normalize(self, embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, a_min=1e-12, a_max=None)
        return embeddings / norms

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        texts = [text.replace("\n", " ") if text else " " for text in texts]
        norm = kwargs.get("norm", self.global_config.embedding_return_as_normalized)
        max_length = kwargs.get("max_length", self.max_length)

        if self.backend == "flagembedding":
            outputs = self.model.encode(
                texts,
                batch_size=self.batch_size,
                max_length=max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            embeddings = np.asarray(outputs["dense_vecs"])
            if norm:
                embeddings = self._normalize(embeddings)
            return embeddings

        embeddings = np.asarray(
            self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=norm,
            )
        )
        return embeddings

    def batch_encode(self, texts: List[str], **kwargs) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        if len(texts) <= self.batch_size:
            return self.encode(texts, **kwargs)

        results = []
        batch_indexes = list(range(0, len(texts), self.batch_size))
        for i in tqdm(batch_indexes, desc="Batch Encoding"):
            results.append(self.encode(texts[i:i + self.batch_size], **kwargs))
        return np.concatenate(results)
