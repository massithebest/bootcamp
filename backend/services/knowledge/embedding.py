"""PoC 문서 검색용 청킹과 해싱 임베딩.

폐쇄망에서 모델 다운로드 없이 동작하도록 문자 n-gram 을 고정 길이 벡터로 해싱한다.
표기 변형·부분 일치에는 강하지만 동의어 같은 의미 유사도는 잡지 못한다. 운영에서는
`get_embedder()` 가 돌려주는 객체만 사내 임베딩(`services/production/milvus_client.py`
의 `get_embedding_function`)으로 바꾸면 된다.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import re
import unicodedata

import numpy as np

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


@dataclass(frozen=True)
class Chunk:
    index: int
    start: int
    text: str


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """Markdown 제목·빈 줄로 나눈 문단을 `size` 자까지 묶고, 긴 문단은 `overlap` 자씩 겹쳐 자른다."""

    bounds = [0, *(m.start() for m in re.finditer(r"\n\s*\n|\n(?=#)", text)), len(text)]
    spans = [(a, b) for a, b in zip(bounds, bounds[1:]) if text[a:b].strip()]
    pieces: list[tuple[int, int]] = []
    for a, b in spans:
        if pieces and b - pieces[-1][0] <= size:
            pieces[-1] = (pieces[-1][0], b)
        elif b - a <= size:
            pieces.append((a, b))
        else:
            for cut in range(a, b, size - overlap):
                pieces.append((cut, min(cut + size, b)))
                if cut + size >= b:
                    break
    chunks: list[Chunk] = []
    for a, b in pieces:
        lead = len(text[a:b]) - len(text[a:b].lstrip())
        chunks.append(Chunk(len(chunks), a + lead, text[a:b].strip()))
    return chunks


class HashingEmbedder:
    """단어별 문자 2·3-gram 을 blake2b 로 `dim` 차원에 해싱한 L2 정규화 벡터."""

    name = "hashing-char23-2048"

    def __init__(self, dim: int = 2048):
        self.dim = dim

    def _features(self, text: str) -> dict[int, float]:
        counts: dict[int, float] = {}
        for word in re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()):
            padded = f"<{word}>"
            for n in (2, 3):
                for i in range(len(padded) - n + 1):
                    digest = blake2b(padded[i:i + n].encode(), digest_size=8).digest()
                    key = int.from_bytes(digest, "little")
                    bucket = key % self.dim
                    sign = 1.0 if (key >> 63) & 1 else -1.0
                    counts[bucket] = counts.get(bucket, 0.0) + sign
        return counts

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for bucket, value in self._features(text).items():
                matrix[row, bucket] = np.sign(value) * np.log1p(abs(value))
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms > 0)


_embedder = HashingEmbedder()


def get_embedder() -> HashingEmbedder:
    return _embedder
