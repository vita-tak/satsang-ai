import sys
import argparse
sys.path.insert(0, ".")

from pathlib import Path

from src.config import PDF_PATH
from src.ingestion.parsers.pdf_parser import load_document, load_pages
from src.ingestion.chunker import chunk_document, chunk_baya
from src.ingestion.metadata_generator import generate_metadata
from src.ingestion.embedder import store_chunks

BAYA_PATH = "data/sources/Be-As-You-Are-(The-Teachings-of-Ramana-Maharshi)-David-Godman-1985.pdf"
BAYA_MAIN_START = 8
BAYA_MAIN_END = 118
BAYA_GLOSSARY_START = 118
BAYA_GLOSSARY_END = 132


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only N chunks")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N chunks")
    args = parser.parse_args()

    print("=== Talks with Sri Ramana Maharshi ===")
    talks_text = load_document(Path(PDF_PATH))
    talks_chunks = chunk_document(talks_text)
    print(f"Found {len(talks_chunks)} chunks")

    print("\n=== Be As You Are ===")
    baya_path = Path(BAYA_PATH)
    baya_main = load_pages(baya_path, BAYA_MAIN_START, BAYA_MAIN_END)
    baya_glossary = load_pages(baya_path, BAYA_GLOSSARY_START, BAYA_GLOSSARY_END)
    baya_chunks = chunk_baya(baya_main, baya_glossary)
    print(f"Found {len(baya_chunks)} chunks")

    all_chunks = talks_chunks + baya_chunks
    print(f"\nTotal: {len(all_chunks)} chunks")

    end = args.offset + args.limit if args.limit else len(all_chunks)
    target = all_chunks[args.offset:end]

    if args.offset or args.limit:
        print(f"Processing chunks {args.offset}-{end} of {len(all_chunks)}")

    print("\nGenerating metadata...")
    enriched = generate_metadata(target)

    print("Embedding and storing...")
    collection = store_chunks(enriched)

    print(f"\nDone. Collection contains {collection.count()} documents.")


if __name__ == "__main__":
    main()