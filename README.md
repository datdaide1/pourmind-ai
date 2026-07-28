<div align="center">

# 🍸 PourMind AI

### Agentic intelligence behind every pour.

**One AI platform. Two purpose-built experiences:** a personal Mixologist for consumers and a Bar Intelligence Copilot for F&B teams.

[![CI](https://github.com/datdaide1/pourmind-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/datdaide1/pourmind-ai/actions/workflows/ci.yml)
[![AI](https://img.shields.io/badge/Product-Agentic_AI-7C3AED)](#-the-agent-experience)
[![B2C](https://img.shields.io/badge/B2C-Personal_Mixologist-E11D48)](#-the-agent-experience)
[![B2B](https://img.shields.io/badge/B2B-Bar_Intelligence-F59E0B)](#-the-agent-experience)
[![LangGraph](https://img.shields.io/badge/Agents-LangGraph-1C3C3C)](https://www.langchain.com/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Web-Next.js_16-000000?logo=next.js)](https://nextjs.org/)
[![Qdrant](https://img.shields.io/badge/Knowledge-Qdrant-DC244C)](https://qdrant.tech/)
[![License](https://img.shields.io/badge/License-Proprietary-blue)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active_Prototype-16A34A)](#project-status)

</div>

---

> **PourMind AI turns cocktail intent into informed action.** It combines specialized agents, trusted knowledge retrieval, deterministic beverage tools, and adaptive UI to help consumers discover the right drink while helping hospitality teams design, cost, and operate better menus.

## ✨ Why PourMind

Most cocktail products stop at recipe search. PourMind treats every request as a decision that may need context, reasoning, retrieval, calculation, and a purpose-built interface.

- **For consumers:** discover cocktails by taste, mood, occasion, ingredients, and constraints.
- **For professionals:** explore recipes, calculate cost and ABV, evaluate substitutions, and support menu decisions.
- **For both:** receive explainable recommendations grounded in a structured cocktail knowledge base.

## 🤖 The agent experience

| Experience | Designed for | What the agent does |
| --- | --- | --- |
| **Personal Mixologist** | Home users and cocktail enthusiasts | Understands preferences, retrieves relevant cocktails, explains recommendations, and proposes practical substitutions. |
| **Bar Intelligence Copilot** | Bartenders, bar managers, and F&B teams | Supports recipe development, ingredient decisions, cost and ABV calculation, and menu exploration. |
| **Agent Tool Layer** | Both experiences | Combines semantic retrieval with deterministic cost, ABV, and substitution tools instead of relying on model guesses. |

Agent responses are streamed as typed text and Server-Driven UI blocks, allowing the interface to present cards, carousels, rationales, and quick actions appropriate to each task.

## 🧠 Core capabilities

- Multi-agent routing for distinct B2C and B2B intents
- Semantic cocktail, ingredient, and venue discovery
- Grounded retrieval from a Qdrant knowledge base
- Deterministic recipe cost and alcohol-by-volume calculations
- Ingredient substitution recommendations
- Streaming responses over Server-Sent Events
- Typed Server-Driven UI components
- Conversation persistence and guest-session migration
- Offline agent tests and optional evaluation workflows

## 🧩 Technology

| Layer | Technology |
| --- | --- |
| Agent orchestration | LangGraph, LangChain |
| Agent API | Python 3.11, FastAPI |
| Agent tools | Retrieval, substitution, cost, and ABV engines |
| Knowledge layer | Qdrant, structured cocktail datasets, embeddings |
| Application state | PostgreSQL, Redis |
| Agent experience | Next.js 16, React 19, typed SSE and SDUI |
| Quality | Pytest, ESLint, TypeScript, Playwright, agent evals |

## 🗂️ Workspace

```text
.
├── apps/
│   └── web/                    # Next.js agent experience and SDUI
├── services/
│   └── agent-api/
│       ├── app/agents/         # LangGraph routing and specialist agents
│       ├── app/tools/          # Retrieval, substitution, cost, and ABV tools
│       ├── app/api/            # FastAPI endpoints and streaming
│       ├── evals/              # Agent evaluation workflows
│       └── tests/              # Offline and integration tests
├── pipelines/
│   └── knowledge-base/         # Cleaning, embedding, and Qdrant ingestion
├── scripts/                    # Repository-level smoke utilities
├── package.json                # Root workspace commands
├── pnpm-workspace.yaml
└── README.md
```

## 🚀 Quick start

### Prerequisites

- Python 3.11+
- Node.js 22+
- pnpm 11+
- PostgreSQL, Redis, and Qdrant
- An OpenAI-compatible model provider key

### 1. Clone and configure

```bash
git clone https://github.com/datdaide1/pourmind-ai.git
cd pourmind-ai
cp .env.example .env
```

Complete the required values in `.env`. Never commit credentials.

### 2. Start the agent API

```bash
cd services/agent-api
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. OpenAPI is available at `/docs` and health status at `/health`.

### 3. Start the agent experience

From the repository root:

```bash
pnpm install --frozen-lockfile
pnpm dev:web
```

Open `http://localhost:3000`.

## ✅ Quality checks

```bash
# Offline agent and tool tests
cd services/agent-api
python -m pytest tests/test_agents.py tests/test_tools.py

# Full integration suite — requires configured test services
python -m pytest tests

# Frontend checks from the repository root
pnpm lint:web
pnpm build:web
pnpm test:e2e
```

## ⚙️ Configuration

Use [.env.example](.env.example) as the configuration contract. Hosted service credentials and model-provider keys must be supplied through environment variables.

## Project status

PourMind AI is an active product prototype. The agent architecture, knowledge pipeline, streaming UI, and core tools are implemented. Authentication, restricted production CORS, deployment hardening, and production observability remain in progress.

## 🔒 License

PourMind AI is proprietary software. The source is visible for evaluation and portfolio review, but no permission is granted to copy, modify, distribute, deploy, sublicense, or create derivative works. See [LICENSE](LICENSE).
