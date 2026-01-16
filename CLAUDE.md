# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

French-language company search application that extracts structured business criteria from natural language queries using LLM (OpenRouter/Gemini). Two modes: multi-turn Chat and single-request Direct extraction.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python api.py                        # Run server on localhost:8000
uvicorn api:app --reload             # Dev server with auto-reload
alembic upgrade head                 # Run database migrations
```

### Frontend (Next.js 14)
```bash
cd frontend
npm install
npm run dev                          # Dev server on localhost:3000
npm run build                        # Production build
npm run lint                         # Run linting
```

### Testing
```bash
python test_agent_api.py             # Integration tests for conversation API
python test_inference.py             # LLM inference tests
```

## Architecture

```
Frontend (Next.js 14 + Zustand)  →  Backend (FastAPI)  →  PostgreSQL
         ↓                                  ↓
    Chat/Direct modes              OpenRouter API (Gemini 2.5)
```

### Key Data Flow
1. User query → Frontend (`app/page.tsx` with mode toggle)
2. Chat mode: `POST /api/v1/conversations/` → `conversation_router.py` → `agent_service.py` → PostgreSQL
3. Direct mode: `POST /extract` → `extraction_service.py` → immediate JSON response
4. LLM extracts 5 criteria sections: localisation, activite, taille_entreprise, criteres_financiers, criteres_juridiques

### Backend Services (`backend/services/`)
- `extraction_service.py` - Single LLM call for criteria extraction
- `agent_service.py` - Decides extract vs clarify, manages conversation flow
- `conversation_service.py` - CRUD for conversations/messages
- `activity_matcher.py` - Semantic search using OpenAI embeddings to match activities to NAF codes (used by chat mode)

Note: `sector_matcher.py` (root-level) is deprecated; use `services/activity_matcher.py` instead.

### Frontend State (`frontend/stores/`)
- `conversationStore.ts` - Zustand store for conversation state, API calls, error handling

## Environment Variables

### Backend (`.env`)
```
OPENROUTER_API_KEY=<required>        # LLM API key
OPENROUTER_MODEL=google/gemini-2.5-flash-lite
DATABASE_URL=<optional>              # Required only for chat mode
OPENAI_API_KEY=<optional>            # For activity embeddings (chat mode)
```

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Database Notes

- PostgreSQL with async support (asyncpg driver)
- Render provides `postgres://` URLs; backend auto-converts to `postgresql+asyncpg://`
- NullPool configured for serverless compatibility
- `/extract` endpoint works without database; `/api/v1/conversations/*` requires it

## Deployment

- Backend: Render (see `render.yaml` and `RENDER_DEPLOYMENT.md`)
- Frontend: Vercel (see `frontend/VERCEL_SETUP.md`)
- CORS currently allows all origins - restrict in production
