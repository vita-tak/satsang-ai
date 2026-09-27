import os

from dotenv import load_dotenv

load_dotenv(".env.local")

# API keys
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Paths
PDF_PATH = "data/sources/Talks-with-Sri-Ramana-Maharshi.pdf"
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")

# Models
EMBEDDING_MODEL = "text-embedding-3-small"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
COLLECTION_NAME = "satsang"

# Retrieval
TOP_K = 5
RERANK_CANDIDATES = 10