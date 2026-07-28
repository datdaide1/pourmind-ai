# PourMind AI

PourMind AI is an agentic cocktail platform designed for consumers and food-and-beverage teams. It combines specialized agents, structured knowledge retrieval, deterministic beverage calculations, and a streaming web interface in one product workspace.

[![CI](https://github.com/datdaide1/pourmind-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/datdaide1/pourmind-ai/actions/workflows/ci.yml)
[![Product](https://img.shields.io/badge/Product-Agentic_AI-5B4B8A)](#product-scope)
[![B2C](https://img.shields.io/badge/B2C-Personal_Mixologist-2F6F9F)](#product-scope)
[![B2B](https://img.shields.io/badge/B2B-Bar_Intelligence-B7791F)](#product-scope)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-2F4F4F)](https://www.langchain.com/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-00897B)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Web-Next.js_16-111111)](https://nextjs.org/)
[![Qdrant](https://img.shields.io/badge/Knowledge-Qdrant-B83280)](https://qdrant.tech/)
[![License](https://img.shields.io/badge/License-Proprietary-4A5568)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active_Prototype-2F855A)](#project-status)

> The consumer experience helps people discover suitable drinks and understand recommendations. The professional experience supports recipe development, ingredient substitution, cost analysis, ABV calculation, and menu planning.

## Product scope

| Experience | Primary users | Supported workflows |
| --- | --- | --- |
| Personal Mixologist | Home users and cocktail enthusiasts | Preference discovery, cocktail recommendations, explanations, and practical substitutions |
| Bar Intelligence Copilot | Bartenders, bar managers, and F&B teams | Recipe exploration, ingredient decisions, cost and ABV calculation, and menu analysis |
| Shared agent platform | Both experiences | Intent routing, semantic retrieval, deterministic tools, streamed responses, and structured UI output |

Recommendations are grounded in a structured cocktail knowledge base. Calculations such as recipe cost and alcohol by volume are handled by deterministic tools rather than generated estimates.

## Current capabilities

- Intent routing between consumer and professional workflows
- Semantic search across cocktails, ingredients, and venue data
- Retrieval from a Qdrant-backed knowledge base
- Recipe cost and alcohol-by-volume calculations
- Ingredient substitution recommendations
- Streaming responses over Server-Sent Events
- Typed Server-Driven UI components
- Conversation persistence and guest-session migration
- Offline agent tests and optional evaluation workflows

## System architecture

| Layer | Implementation |
| --- | --- |
| Agent orchestration | LangGraph and LangChain |
| API | Python 3.11 and FastAPI |
| Agent tools | Retrieval, substitution, cost, and ABV engines |
| Knowledge layer | Qdrant, embeddings, and structured cocktail datasets |
| Application state | PostgreSQL and Redis |
| Web application | Next.js 16, React 19, typed SSE, and Server-Driven UI |
| Quality controls | Pytest, ESLint, TypeScript, Playwright, and agent evaluations |

## Repository structure

```text
.
├── apps/
│   └── web/                    # Next.js web application and SDUI components
├── services/
│   └── agent-api/
│       ├── app/agents/         # Routing and specialist agents
│       ├── app/tools/          # Retrieval, substitution, cost, and ABV tools
│       ├── app/api/            # FastAPI endpoints and streaming transport
│       ├── evals/              # Agent evaluation workflows
│       └── tests/              # Offline and integration tests
├── pipelines/
│   └── knowledge-base/         # Data preparation and Qdrant ingestion
├── scripts/                    # Repository-level smoke utilities
├── package.json                # Workspace commands
├── pnpm-workspace.yaml
└── README.md
```

All paths in the project documentation are relative to the repository root.

## Getting started

### Prerequisites

- Python 3.11 or later
- Node.js 22 or later
- pnpm 11 or later
- PostgreSQL, Redis, and Qdrant
- An OpenAI-compatible model-provider key

### Installation

```bash
git clone https://github.com/datdaide1/pourmind-ai.git
cd pourmind-ai
cp .env.example .env
```

Complete the required values in `.env`. Credentials and provider keys must not be committed.

### Agent API

```bash
cd services/agent-api
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. OpenAPI documentation is exposed at `/docs`, and health status is exposed at `/health`.

### Web application

From the repository root:

```bash
pnpm install --frozen-lockfile
pnpm dev:web
```

The application is available at `http://localhost:3000`.

## Validation

Run the offline agent and tool tests:

```bash
cd services/agent-api
python -m pytest tests/test_agents.py tests/test_tools.py
```

Run the frontend checks from the repository root:

```bash
pnpm lint:web
pnpm build:web
pnpm test:e2e
```

The full backend integration suite requires configured PostgreSQL, Redis, Qdrant, and model-provider services.

## Configuration

Use [.env.example](.env.example) as the configuration contract. Runtime credentials and model-provider keys must be supplied through environment variables.

## Project status

PourMind AI is an active product prototype. The agent architecture, knowledge pipeline, streaming interface, and core tools are implemented. Authentication, restricted production CORS, deployment hardening, and production observability remain in progress.

## License

PourMind AI is proprietary software. The source is available for evaluation and portfolio review, but no permission is granted to copy, modify, distribute, deploy, sublicense, or create derivative works. See [LICENSE](LICENSE).
