import os
from pathlib import Path

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
# Chunks scoring below this are left out of the guide's background; none left means the context
# is insufficient. The CrossEncoder gives logits: in a free calibration on invented pairs,
# unrelated pairs scored about -11.4, loosely related ones -10.5 and up, related ones above 0,
# so only chunks at that floor are dropped. Provisional until tuned on real scores.
CONTEXT_MIN_SCORE = -11.0

# Chat
CHAT_RATE_LIMIT = "10/minute"

# Guide content the owner maintains: prompt parts, crisis lines, decline sentences, risk phrases.
# Resolved from this file, so the paths hold whatever the working directory.
GUIDE_DIR = Path(__file__).resolve().parent.parent / "guide"
PROMPT_PARTS_DIR = GUIDE_DIR / "parts"
CRISIS_LINES_PATH = GUIDE_DIR / "crisis_lines.json"
DECLINE_PATH = GUIDE_DIR / "decline.json"
TREATMENT_FALLBACK_PATH = GUIDE_DIR / "treatment_fallback.json"
RISK_PHRASES_DIR = GUIDE_DIR / "risk_phrases"
# The language whose decline sentence and risk phrases are used when there are none for the
# language of the person's message
FALLBACK_LANGUAGE = "en"

# Guide: hard word limits from the guide prompt's Section B (the soft limits are for tuning only)
POINTING_MAX_WORDS = 300
EXPLANATORY_MAX_WORDS = 450
# A reply that breaks the treatment rule is written again up to this many times, each naming the
# banned words it used; if the reply after the last rewrite still breaks it, a fixed reply is sent
MAX_TREATMENT_REWRITES = 2
CLASSIFIER_MAX_TOKENS = 400
# The classifier decides risk, so the same message should get the same decision each time. At the
# API default (1.0) the grief message was `none` in two rounds and `unsure` in a third. The
# installed SDK (1.8.0) has no typed temperature parameter, so it is sent in extra_body.
CLASSIFIER_TEMPERATURE = 0
# Room above the hard word limits, so a reply is never cut off mid-sentence; a pointing reply
# also carries its tool call
REPLY_MAX_TOKENS = {"pointing": 1024, "explanatory": 1024, "social": 300, "crisis": 600}
# The last five exchanges. Earlier turns come in pairs, so the window starts with the person.
HISTORY_LIMIT = 10

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
