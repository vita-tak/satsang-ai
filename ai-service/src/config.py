import os

from dotenv import load_dotenv

load_dotenv(".env.local")

# API keys
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

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

# Chat
CHAT_RATE_LIMIT = "10/minute"

# Speech to text
WHISPER_MODEL = "whisper-1"
WHISPER_PROMPT_MAX_TOKENS = 220
WHISPER_TOKENIZER = "openai/whisper-small"
TRANSCRIBE_MAX_BYTES = 5 * 1024 * 1024
TRANSCRIBE_RATE_LIMIT = "10/minute"

# Text to speech
TTS_MODEL = "gemini-3.8-flash-tts"
TTS_VOICE = "Charon"
TTS_AUDIO_FORMAT = "audio/l16"
TTS_SAMPLE_RATE = 24000
TTS_FIRST_CHUNK_TIMEOUT_SECONDS = 4
DIRECTOR_MAX_TOKENS = 1024
DIRECTOR_TIMEOUT_SECONDS = 5
