# PourMind AI

PourMind AI is the intelligence layer for modern mixology. It brings consumer discovery, professional beverage operations, and machine-assisted decision-making into one agentic product platform.

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

> Cocktail software has traditionally been split between static recipe libraries for consumers and disconnected operational tools for professionals. PourMind AI replaces that divide with a shared agent platform that understands intent, retrieves domain knowledge, performs reliable calculations, and returns an interface appropriate to the decision being made.

## Product thesis

A cocktail recommendation is rarely just a search query. The useful answer depends on taste, available ingredients, dietary constraints, occasion, technique, budget, inventory, alcohol content, and commercial context. PourMind AI treats these factors as parts of one decision system rather than isolated filters.

For consumers, the product acts as a personal mixologist: it translates subjective preferences into recommendations that are specific, explainable, and practical. For hospitality teams, it acts as a bar intelligence copilot: it helps turn creative ideas into recipes and menu decisions that can be evaluated against cost, ABV, ingredient availability, and operational constraints.

The long-term opportunity is broader than cocktail discovery. PourMind AI is designed as an operating layer for beverage intelligence, connecting guest intent with the knowledge and economics behind every pour.

## Product scope

| Experience | Primary users | Supported workflows |
| --- | --- | --- |
| Personal Mixologist | Home users and cocktail enthusiasts | Converts taste, mood, occasion, ingredients, and constraints into explainable recommendations and practical next steps |
| Bar Intelligence Copilot | Bartenders, bar managers, and F&B teams | Accelerates recipe development, substitution decisions, cost control, ABV analysis, and menu exploration |
| Shared agent platform | Product and operational workflows | Coordinates intent routing, semantic retrieval, deterministic tools, streamed responses, and structured UI output |

Recommendations are grounded in a structured cocktail knowledge base. Calculations such as recipe cost and alcohol by volume are handled by deterministic tools rather than generated estimates.

## Why PourMind AI

### One platform, two commercial surfaces

The B2C experience creates a direct relationship with drinkers through discovery and personalization. The B2B experience converts the same intelligence foundation into professional workflows for bars, restaurants, hotels, beverage brands, and hospitality operators. A shared platform allows knowledge, tooling, and product learning to compound across both surfaces.

### Agentic execution, not a chat wrapper

The system does not send every prompt to one general-purpose model and hope for a plausible answer. It routes requests to specialized workflows, retrieves relevant domain context, invokes deterministic tools when precision matters, and returns typed interface components that the application can render safely.

### Domain knowledge with operational consequences

Recipes are connected to ingredients, substitutions, serving context, price data, and beverage calculations. This makes PourMind AI useful beyond inspiration: the platform is structured to support decisions that affect what a guest orders, what a bartender builds, and what an operator can profitably place on a menu.

### Designed to become infrastructure

The repository separates the agent API, web experience, knowledge pipeline, and deterministic tools so each layer can evolve independently. This creates a foundation for future integrations with inventory systems, menu platforms, point-of-sale data, supplier catalogs, and venue-specific operating rules.

## How the agent works

```text
User intent
    -> Intent router
    -> Consumer or professional workflow
    -> Knowledge retrieval and deterministic tools
    -> Response synthesis
    -> Streamed text and typed UI blocks
```

This division keeps language generation focused on understanding and explanation while delegating retrieval and numerical work to components that can be inspected and tested.

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

PourMind AI is an active product prototype with an implemented agent architecture, knowledge pipeline, streaming interface, semantic retrieval layer, and deterministic cost, ABV, and substitution tools.

The current repository demonstrates the core product loop and technical foundation. Authentication, restricted production CORS, deployment hardening, production observability, live commercial integrations, and venue-specific operating profiles remain in progress. No production adoption or commercial performance claims are implied by this prototype.

## License

PourMind AI is proprietary software. The source is available for evaluation and portfolio review, but no permission is granted to copy, modify, distribute, deploy, sublicense, or create derivative works. See [LICENSE](LICENSE).
