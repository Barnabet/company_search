# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

French-language company search application that extracts structured business criteria from natural language queries using LLM (OpenRouter/Gemini). Stateless chat interface with two-panel design. Uses pgvector for activity embeddings storage.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python api.py                        # Run server on localhost:8000
uvicorn api:app --reload             # Dev server with auto-reload
```

### Frontend (Next.js 14)
```bash
cd frontend
npm install
npm run dev                          # Dev server on localhost:3000
npm run build                        # Production build
npm run lint                         # Run linting
```

### Populate Embeddings Database
```bash
cd backend
python scripts/populate_embeddings.py    # Load activities + embeddings into PostgreSQL
```

## Architecture

```
Frontend (Next.js 14 + Zustand)  →  Backend (FastAPI)
         ↓                                  ↓
    Two-panel chat UI              OpenRouter API (Gemini 2.5)
    Messages in Zustand                     ↓
                                   Activity Matcher
                                   (pgvector or file fallback)
                                           ↓
                                   Company Count API
```

### Key Data Flow
1. User types query in chat panel
2. Frontend sends full message history to `POST /api/v1/chat`
3. Backend extracts criteria via LLM (or rejects if too vague)
4. Backend matches activities to NAF codes via embeddings (pgvector or file)
5. Backend queries external company API for count
6. Response returns to frontend with extraction + count
7. Left panel shows current search criteria, right panel shows chat

### Backend Services (`backend/services/`)
- `agent_service.py` - LLM extraction, always extracts or rejects (no clarify)
- `activity_matcher.py` - Semantic search using pgvector (with file-based fallback)
- `extraction_service.py` - Single-shot extraction (used by `/extract` endpoint)
- `api_transformer.py` - Transforms extraction to API request format
- `company_api_client.py` - Calls external company count API

### Database (`backend/database.py`)
- PostgreSQL with pgvector extension for activity embeddings
- Falls back to pickle file if DATABASE_URL not set
- Connection pool managed via asyncpg

### Frontend Components (`frontend/components/`)
- `SearchFieldsPanel.tsx` - Left panel showing extraction criteria and company count
- `Chat/ChatPanel.tsx` - Right panel with chat interface
- `Chat/ChatMessage.tsx` - Individual message bubble

### Frontend State (`frontend/stores/`)
- `conversationStore.ts` - Zustand store managing messages locally (stateless backend)

## Environment Variables

### Backend (`.env`)
```
OPENROUTER_API_KEY=<required>        # LLM API key
OPENROUTER_MODEL=google/gemini-2.5-flash-lite
OPENAI_API_KEY=<required>            # For activity embeddings
DATABASE_URL=<optional>              # PostgreSQL with pgvector (falls back to file)
```

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Endpoints

- `GET /` - Health check
- `GET /health` - Health status with database/embeddings info
- `POST /api/v1/chat` - Main chat endpoint (stateless, send full message history)
- `POST /extract` - Single-shot extraction (no conversation context)

## Embeddings Storage

### Option 1: PostgreSQL + pgvector (recommended)
- Set `DATABASE_URL` environment variable
- Run `python scripts/populate_embeddings.py` to load data
- Enables fast similarity search via SQL
- Table: `activities` with `embedding vector(1536)` column

### Option 2: File-based fallback
- If DATABASE_URL not set, uses `data/activites_embeddings_openai.pkl`
- Auto-generated on first use if OpenAI API key is set
- Good for local development without PostgreSQL

## Database Schema

```sql
CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    label_normalized TEXT NOT NULL,
    naf_codes TEXT[] NOT NULL DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- IVFFlat index for fast similarity search
CREATE INDEX activities_embedding_idx
ON activities USING ivfflat (embedding vector_cosine_ops);
```

## Deployment

- Backend: Render (see `render.yaml`)
- Frontend: Vercel
- Database: Render PostgreSQL with pgvector extension enabled
