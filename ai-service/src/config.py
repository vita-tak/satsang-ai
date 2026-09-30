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

# Speech to text
WHISPER_MODEL = "whisper-1"
# Whisper keeps only the last 224 tokens of its prompt, so the glossary list stays a few under it
WHISPER_PROMPT_MAX_TOKENS = 220
# The hub repository whose tokenizer is Whisper's own, used to count prompt tokens
WHISPER_TOKENIZER = "openai/whisper-small"
# A 3 minute recording at the frontend's speech bitrate is about 0.7 MB
TRANSCRIBE_MAX_BYTES = 5 * 1024 * 1024
TRANSCRIBE_RATE_LIMIT = "10/minute"