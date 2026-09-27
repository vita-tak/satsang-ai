# Satsang AI

A contemplative chat interface for self-inquiry in the tradition of Ramana Maharshi. Ask questions about the teachings, get guided in the practice of self-inquiry, or explore Sanskrit terms and concepts.

## What it does

Ask a question about self-inquiry, Ramana's teachings, or a Sanskrit concept. The system classifies your intent and routes it to the right handler: direct guidance for self-inquiry practice, RAG-grounded answers for questions about the teachings, soft acknowledgment for personal struggles, and precise definitions for Sanskrit terms.

## Tech stack

| Component       | Technology                                          |
| --------------- | --------------------------------------------------- |
| Frontend        | Next.js, TypeScript, Bun                            |
| API             | FastAPI, Python 3.12                                |
| Agent framework | LangGraph                                           |
| LLM             | Claude Haiku (classification) + Sonnet (generation) |
| Embeddings      | OpenAI text-embedding-3-small                       |
| Vector database | ChromaDB                                            |
| Keyword search  | BM25 via rank-bm25                                  |
| Re-ranking      | sentence-transformers CrossEncoder                  |
| Rate limiting   | slowapi (10 requests/minute per IP)                 |

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

### Prerequisites

Python 3.12+, Bun, Anthropic API key, OpenAI API key

### Backend

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

### Frontend

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

Returns:

```json
{ "response": "...", "session_id": "abc-123" }
```

Pass `session_id` back on subsequent requests to maintain conversation history within a session.

## Intent routing

| Intent              | Trigger                                        | Handler                     |
| ------------------- | ---------------------------------------------- | --------------------------- |
| `self_inquiry`      | Seeker wants direct guidance in practice       | Guided inquiry node, no RAG |
| `satsang`           | Questions about teachings, Self, consciousness | RAG + generation            |
| `definition`        | Sanskrit term or concept                       | RAG + precise definition    |
| `personal_struggle` | Sharing difficulty with practice               | RAG + soft generation       |
| `off_topic`         | Unrelated to self-inquiry or teachings         | Polite decline              |
