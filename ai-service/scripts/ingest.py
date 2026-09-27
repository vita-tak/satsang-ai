import sys
sys.path.insert(0, ".")

from pathlib import Path

from src.config import PDF_PATH
from src.ingestion.parsers.pdf_parser import load_document
from src.ingestion.chunker import chunk_document
from src.ingestion.metadata_generator import generate_metadata
from src.ingestion.embedder import store_chunks

# Run once locally to build the ChromaDB vector store.
# Output is persisted to data/chroma/ and uploaded to the server.


def main() -> None:
    print("Loading PDF...")
    text = load_document(Path(PDF_PATH))

    print("Chunking document...")
    chunks = chunk_document(text)
    print(f"Found {len(chunks)} chunks")

    print("Generating metadata...")
    enriched = generate_metadata(chunks)

    print("Embedding and storing...")
    collection = store_chunks(enriched)

    print(f"Done. Collection contains {collection.count()} documents.")


if __name__ == "__main__":
    main()