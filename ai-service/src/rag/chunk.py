from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    """
    One retrieved passage with its metadata. Only `text`, scrubbed, ever reaches the model; the
    reference, chunk type, summary and score stay in the retrieval layer.
    """

    text: str
    reference: str
    chunk_type: str
    summary: str
    score: float
