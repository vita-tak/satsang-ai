# Satsang AI

A contemplative chat interface for self-inquiry in the tradition of Ramana Maharshi. Ask questions about the teachings, get guided in the practice of self-inquiry, or explore Sanskrit terms and concepts.

## What it does

Ask a question about self-inquiry, Ramana's teachings, or a Sanskrit concept, or write a longer letter about your practice. You choose how the guide answers (one of four response modes, below); the system classifies what your message is doing and routes it: RAG-grounded answers from the texts, direct guidance without retrieval in Self-inquiry mode, precise definitions for Sanskrit terms, and a plain, caring reply that points to help when a message suggests risk of harm.

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
{ "message": "Who am I?", "session_id": null, "mode": "satsang" }
```

`mode` is optional: `satsang`, `teachings` (default), `ramana` or `self_inquiry`.

Returns:

```json
{ "response": "...", "session_id": "abc-123" }
```

Pass `session_id` back on subsequent requests to maintain conversation history within a session.

## Response modes

| Mode           | How the guide answers                                                        |
| -------------- | ---------------------------------------------------------------------------- |
| `satsang`      | Adaptive: a pointing, a short teaching from the texts, or a direct question, chosen for the seeker in the moment; a long letter gets a brief acknowledgment and one pointing or question |
| `teachings`    | Quote, explanation, closing question (default)                               |
| `ramana`       | As Ramana answered: his own words without comment, or a sentence or two in his manner |
| `self_inquiry` | No teaching: a question or a direct pointing at the seeker, now (no RAG)     |

## Intent routing

The classifier sees the guide's previous reply, so short answers to the guide's questions are
understood, and writes a standalone search query for retrieval. The mode never affects it.

| Intent       | Trigger                                              | Handler                                                  |
| ------------ | ---------------------------------------------------- | -------------------------------------------------------- |
| `teaching`   | Questions about the teachings, Self, mind, world     | Mode prompt (RAG, except in Self-inquiry mode)           |
| `practice`   | Wants guidance in practice, or answers the guide     | Mode prompt (RAG, except in Self-inquiry mode)           |
| `struggle`   | Shares a personal difficulty                         | Mode prompt (RAG, except in Self-inquiry mode)           |
| `definition` | Sanskrit term or concept                             | RAG + precise definition, same in every mode             |
| `social`     | Greeting, thanks, goodbye                            | Short reply, no RAG, same in every mode                  |
| `crisis`     | Possible risk of harm                                | Plain, caring reply pointing to help; no RAG, no quotes  |
| `off_topic`  | Unrelated to self-inquiry or teachings               | Polite decline                                           |
