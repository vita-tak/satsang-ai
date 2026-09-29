# Satsang AI

A contemplative chat interface for self-inquiry in the tradition of Ramana Maharshi.

## What it does

Ask a question about the teachings, describe something you're struggling with, or write a longer letter about your practice. The system classifies what your message is doing and routes it accordingly: RAG-grounded answers from the source texts, direct guidance in Self-inquiry mode, precise definitions for Sanskrit terms, and a plain, caring reply when a message suggests risk of harm. You choose how the guide answers through one of four response modes.

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
| Speech-to-text  | Web Speech API                     |

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
{ "message": "Who am I?", "session_id": null, "mode": "satsang" }
```

`mode` is optional: `satsang` (default), `teachings`, `self_inquiry`, or `ramana`.

Pass `session_id` back on subsequent requests to maintain conversation history.
