# QnA RAG Agent

A self-hosted question-answering agent over uploaded documents. Create a knowledge base, drop in PDFs or Office docs, and chat with a **corrective RAG (CRAG)** agent that grades its own retrieval, falls back to a live web search when the knowledge base comes up short, and checks its own answer for hallucinations before replying.

<p align="center">
  <img src="images/agent_graph.png" alt="Agent graph" width="200">
</p>

Built with **FastAPI + LangGraph + LangChain + OpenAI**, **Postgres + pgvector** for storage and retrieval, **Celery + Redis** for background ingestion, **SeaweedFS** for raw document storage, and **MLflow** observability.

---

## How it works

1. **Knowledge bases and chats.** A knowledge base holds documents; a chat is bound to a knowledge base, which can be swapped later anytime.
2. **Background document ingestion.** All documents are processed by a Celery worker in the background, it extracts text with Unstructured, semantically chunks it, embeds it, and stores the vectors.

<p align="center">
  <img src="images/knowledge_base.png" alt="Knowledge base management view" width="760"><br>
</p>

3. **Ask a question:**
   - **retrieve** — ensemble search (pgvector + Postgres full-text) scoped to the chat's Knowledge Base
   - **grade** — an LLM call keeps only genuinely relevant chunks and flags if there aren't enough
   - **web_search** *(conditional)* — Google Search fills the gap when the retrieval falls short
   - **generate** — answers strictly from the retrieved context
   - **check_hallucination** — a second LLM call verifies every claim traces back to context; ungrounded answers loop back to **generate**
4. **Citations.** Each answer is cited, sources can be verified in the UI — click a `[n]` marker to open the full quoted source.

<p align="center">
  <img src="images/chat.png" alt="Chat view with citations and source panel" width="760"><br>
</p>

---

## Quick start

Requires **Docker** and **Docker Compose**.

```bash
# 1. Configure environment
cp .env.example .env
#    Edit .env and set the required secrets:
#      OPENAI_API_KEY   — your OpenAI key
#      DATABASE_URL     — postgresql+asyncpg://qna:qna@postgres:5432/qna (default is fine)
#      JWT_SECRET       — generate: openssl rand -hex 32

# 2. Build and start everything
docker compose up --build
```

This brings up Postgres (pgvector), Redis, SeaweedFS, MLflow, the API, and the Celery worker, and runs `alembic upgrade head` automatically before the API/worker start. Open:

- **http://localhost:8000** — sign in / register
- **http://localhost:8000/app** — the chat app
- **http://localhost:5000** — MLflow UI (if `MLFLOW_ENABLED=true`)
- **http://localhost:9333** — SeaweedFS master UI

---

## Configuration

Configuration is layered: [settings.yaml](settings.yaml) holds defaults, resolved at load time from the environment (and `.env`) by [app/core/config.py](app/core/config.py).

**Required in `.env`** (no defaults):

| Variable           | Purpose                                                                       |
| ------------------ | ----------------------------------------------------------------------------- |
| `OPENAI_API_KEY` | OpenAI access for the LLM (grading, generation, hallucination check, titling) |
| `DATABASE_URL`   | Async SQLAlchemy URL                                                          |
| `JWT_SECRET`     | Signing key for auth tokens                                                   |

**Optional overrides** (defaults in `settings.yaml`):

| Variable                                            | Default                          | Purpose                                                                                           |
| --------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------- |
| `OPENAI_MODEL_ANALYSIS`                           | `gpt-5.4-2026-03-05`           | Model for grading/generation/hallucination checks                                                 |
| `OPENAI_MODEL_FAST`                               | `gpt-5.4-mini-2026-03-17`      | Lighter model for chat title generation                                                           |
| `REDIS_URL`                                       | `redis://localhost:6379/0`     | Celery broker + result backend                                                                    |
| `SEAWEEDFS_ENDPOINT`                              | `http://seaweedfs:8333`        | S3-compatible endpoint for the document store                                                     |
| `SEAWEEDFS_ACCESS_KEY` / `SEAWEEDFS_SECRET_KEY` | `seaweedfs` / `seaweedfs123` | Placeholder credentials — the bundled SeaweedFS runs with no IAM config, so it accepts any value |
| `SEAWEEDFS_BUCKET`                                | `documents`                    | Bucket documents are stored under                                                                 |
| `GOOGLE_API_KEY` / `GOOGLE_CX`                  | *(unset)*                      | Enables the`web_search` node; skipped gracefully when absent                                    |
| `ALLOWED_ORIGINS`                                 | `http://localhost:8000`        | Comma-separated CORS origins                                                                      |
| `LOG_LEVEL`                                       | `info`                         | Log level                                                                                         |
| `MLFLOW_ENABLED`                                  | `false`                        | Toggle MLflow observability                                                                       |
| `MLFLOW_TRACKING_URL`                             | `http://localhost:5000`        | MLflow tracking server URI                                                                        |

**Swappable providers** — edit `settings.yaml`, no code changes:

| Config key            | Options                                                                                                                            | Default               |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `models.embeddings` | `embedding_sentence_transformers` (local, offline) · `embedding_openai`                                                       | sentence-transformers |
| `vectorstore`       | `vectorstore_pgvector` · `vectorstore_chromadb`                                                                               | pgvector              |
| `retrieval`         | `retriever_ensemble` (pgvector + Postgres FTS) · `retriever_ensemble_bm25` · `retriever_vectorstore` · `retriever_bm25` | ensemble              |
| `file_store`        | `file_store_seaweedfs` · `file_store_local` (plain disk)                                                                      | SeaweedFS             |

---

## API reference

Pages:

| Route        | Description        |
| ------------ | ------------------ |
| `GET /`    | Sign in / register |
| `GET /app` | Chat SPA           |

Auth (`/api/auth`):

| Endpoint      | Method | Description                      |
| ------------- | ------ | -------------------------------- |
| `/register` | POST   | Create an account, returns a JWT |
| `/login`    | POST   | Authenticate, returns a JWT      |

Knowledge bases (`/api/knowledge-bases`):

| Endpoint     | Method | Description                                      |
| ------------ | ------ | ------------------------------------------------ |
| `/`        | GET    | List your knowledge bases (with document counts) |
| `/`        | POST   | Create a knowledge base                          |
| `/{kb_id}` | GET    | Fetch one                                        |
| `/{kb_id}` | PATCH  | Rename / update description                      |
| `/{kb_id}` | DELETE | Delete, cascading its documents and chunks       |

Documents (`/api/knowledge-bases/{kb_id}/documents`):

| Endpoint      | Method | Description                                       |
| ------------- | ------ | ------------------------------------------------- |
| `/`         | GET    | List documents and their ingestion status         |
| `/`         | POST   | Upload a file, enqueue background ingestion (202) |
| `/{doc_id}` | GET    | Fetch one, typically to poll status               |
| `/{doc_id}` | DELETE | Delete a document and its chunks                  |

Conversations (`/api/conversations`):

| Endpoint             | Method | Description                                                          |
| -------------------- | ------ | -------------------------------------------------------------------- |
| `/`                | POST   | Create a chat (optionally bound to a KB immediately)                 |
| `/`                | GET    | List your chats                                                      |
| `/{conv_id}`       | GET    | Fetch a chat with full message history + citations                   |
| `/{conv_id}`       | PATCH  | Rename or (re)bind to a knowledge base                               |
| `/{conv_id}`       | DELETE | Delete a chat and its messages                                       |
| `/{conv_id}/chat`  | POST   | Run the CRAG agent for a new message, returns the answer + citations |
| `/{conv_id}/title` | POST   | Fire-and-forget: generate a short title from the first exchange      |

Health:

| Endpoint        | Method | Description    |
| --------------- | ------ | -------------- |
| `/api/health` | GET    | Liveness check |

---

## Observability (MLflow)

When `MLFLOW_ENABLED=true`, each **conversation** maps to **one MLflow run**:

- A run is created on the first message and its id is persisted on the `conversations` row (`mlflow_run_id`), so later turns re-attach to the same run regardless of process restarts.
- Per-turn metrics are logged: retrieved/relevant document counts, whether a web search fired, generation retry count, whether hallucination was detected, and end-to-end latency.

---

## Testing

```bash
pytest
```

Covers config loading, the service container singleton, health endpoint, model/vectorstore registries, retrievers, and metadata filters.

---

## Database migrations

Schema changes are managed with Alembic against `Base.metadata`:

```bash
alembic upgrade head                              # apply all migrations
alembic revision --autogenerate -m "description"  # create a new migration
alembic downgrade -1                              # roll back one
```

`docker-compose.yml` runs `alembic upgrade head` automatically via a one-shot `migrate` service before `api`/`worker` start.
