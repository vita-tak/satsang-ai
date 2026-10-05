# Satsang AI

A contemplative chat interface for self-inquiry.

## What it does

Bring what is on your mind, ask about the practice or an idea, or write a longer letter. A classifier reads each message first for any sign of risk, which always takes a careful crisis reply, and then picks how the guide answers: pointing you back to your own experience, explaining an idea in plain words, or simply answering a greeting. Retrieved passages from the source texts are background only: the guide speaks in its own voice and never quotes or names a teacher, text or tradition.

## Tech stack

| Component       | Technology                         |
| --------------- | ---------------------------------- |
| Frontend        | Next.js, TypeScript, Bun           |
| API             | FastAPI, Python 3.12               |
| Agent framework | LangGraph                          |
| LLM             | Claude Haiku 4.5                   |
| Embeddings      | OpenAI text-embedding-3-small      |
| Vector database | ChromaDB                           |
| Keyword search  | BM25 via rank-bm25                 |
| Re-ranking      | sentence-transformers CrossEncoder |
| Speech-to-text  | OpenAI Whisper                     |

## Project structure

```
satsang-ai/
├── ai-service/          # FastAPI backend + LangGraph agent
│   ├── src/
│   │   ├── ingestion/   # PDF parsing, chunking, embedding pipeline
│   │   ├── rag/         # hybrid retrieval and re-ranking
│   │   ├── agent/       # LangGraph graph, state, and nodes
│   │   └── api/         # FastAPI app and middleware
│   └── scripts/         # ingestion CLI
└── frontend/            # Next.js chat interface
```

## Running locally

**Prerequisites:** Python 3.12+, Bun, Anthropic API key, OpenAI API key

**Backend**

```bash
cd ai-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
# Add ANTHROPIC_API_KEY and OPENAI_API_KEY to .env.local
uvicorn src.api.main:app --reload
```

The ChromaDB vector store is included in the repo and ready to use. API docs at `http://localhost:8000/docs`.

**Frontend**

```bash
cd frontend
bun install
bun dev
```

Open `http://localhost:3000`.

## API

### POST /chat

```json
{ "message": "Who am I?", "session_id": null }
```

Pass `session_id` back on subsequent requests to maintain conversation history.
