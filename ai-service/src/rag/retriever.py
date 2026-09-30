from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import chromadb
from openai import OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from src.config import (
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    RERANK_CANDIDATES,
    TOP_K,
)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-TinyBERT-L-2-v2"
RRF_K = 60


@dataclass
class RetrievedChunk:
    text: str
    reference: str
    chunk_type: str
    summary: str
    score: float


def _tokenize(text: str) -> list[str]:
    """
    Lowercase and split on whitespace.

    BM25 is purely lexical, so consistent tokenization between
    index time and query time is the only requirement.
    """
    return text.lower().split()


def _rrf(
    vector_hits: list[dict],
    bm25_hits: list[dict],
    k: int = RRF_K,
) -> list[dict]:
    """
    Reciprocal Rank Fusion -- merge two ranked lists into one.

    Each document gets a score of 1/(k + rank) from each list it appears in.
    Documents that rank highly in both lists accumulate the most score.
    k=60 is the standard default from the original RRF paper.
    """
    scores: dict[str, float] = {}
    index: dict[str, dict] = {}

    for rank, hit in enumerate(vector_hits, start=1):
        key = hit["document"]
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        index[key] = hit

    for rank, hit in enumerate(bm25_hits, start=1):
        key = hit["document"]
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        index[key] = hit

    ranked_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [index[key] for key in ranked_keys]


class Retriever:
    """
    Hybrid retriever: vector search + BM25, fused with RRF, re-ranked
    with CrossEncoder. Instantiate once at startup.
    """

    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR) -> None:
        self._openai = OpenAI(api_key=OPENAI_API_KEY)

        chroma = chromadb.PersistentClient(path=persist_dir)
        self._collection = chroma.get_collection(name=COLLECTION_NAME)

        all_docs = self._collection.get(include=["documents", "metadatas"])
        self._corpus_documents: list[str] = all_docs["documents"]
        self._corpus_metadatas: list[dict] = all_docs["metadatas"]

        tokenized = [_tokenize(doc) for doc in self._corpus_documents]
        self._bm25 = BM25Okapi(tokenized)

        self._encoder = CrossEncoder(CROSS_ENCODER_MODEL)

        print(f"Retriever ready: {len(self._corpus_documents)} documents indexed")

    def glossary_entries(self) -> list[str]:
        """The text of every glossary entry chunk, read from the existing collection."""
        found = self._collection.get(
            where={"chunk_type": "glossary_entry"},
            include=["documents"],
        )
        return found["documents"]

    def text_chunks(self) -> list[str]:
        """The text of every chunk that is not a glossary entry, from the corpus held in memory."""
        return [
            document
            for document, metadata in zip(self._corpus_documents, self._corpus_metadatas)
            if metadata["chunk_type"] != "glossary_entry"
        ]

    def _vector_search(self, query: str, n: int) -> list[dict]:
        """Embed query and return top-n hits from ChromaDB."""
        embedding = (
            self._openai.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[query],
            )
            .data[0]
            .embedding
        )
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas"],
        )
        return [
            {"document": doc, "metadata": meta}
            for doc, meta in zip(
                results["documents"][0],
                results["metadatas"][0],
            )
        ]

    def _bm25_search(self, query: str, n: int) -> list[dict]:
        """Return top-n hits from the in-memory BM25 index."""
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:n]

        return [
            {
                "document": self._corpus_documents[i],
                "metadata": self._corpus_metadatas[i],
            }
            for i in ranked_indices
            if scores[i] > 0
        ]

    def _rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Score query-document pairs with CrossEncoder and return top_k."""
        pairs = [[query, c["document"]] for c in candidates]
        scores = self._encoder.predict(pairs)

        ranked = sorted(
            zip(scores, candidates),
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            RetrievedChunk(
                text=c["document"],
                reference=c["metadata"]["reference"],
                chunk_type=c["metadata"]["chunk_type"],
                summary=c["metadata"]["summary"],
                score=float(score),
            )
            for score, c in ranked[:top_k]
        ]

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        candidates: int = RERANK_CANDIDATES,
    ) -> list[RetrievedChunk]:
        """
        Retrieve the most relevant chunks for a query.

        Steps:
        1. Run vector search and BM25 search in parallel
        2. Merge ranked lists with Reciprocal Rank Fusion
        3. Re-rank the fused candidates with CrossEncoder
        4. Return the top_k best chunks
        """
        with ThreadPoolExecutor(max_workers=2) as executor:
            vector_future = executor.submit(self._vector_search, query, candidates)
            bm25_future = executor.submit(self._bm25_search, query, candidates)
            vector_hits = vector_future.result()
            bm25_hits = bm25_future.result()

        fused = _rrf(vector_hits, bm25_hits)
        return self._rerank(query, fused, top_k)