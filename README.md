# PR Review Agent

**An agentic AI system for context-aware GitHub Pull Request reviews.**

PR Review Agent analyzes Pull Requests using **four specialized AI reviewers running in parallel**, each with **agent specific repository context**, followed by a dedicated **Validator Agent** and **Review Writer Agent**.

Instead of sending a PR diff to a single LLM and asking it to review everything, the system decomposes code review into specialized tasks and gives each reviewer the context most relevant to its responsibility.

---

## ✨ What Makes This Different?

A simple AI code reviewer might look like:

```text
PR Diff → LLM → Review
```

This project uses a structured multi agent pipeline:

```text
                         GitHub PR
                             │
                             ▼
                      Repository Context
                             │
                             ▼
                   Agent-Specific Context
                             │
              ┌──────────────┼──────────────────────────     
              │              │              │          │   
              ▼              ▼              ▼          ▼
           Quality        Security          Bug     Performance
            Agent          Agent           Agent      Agent
              │              │              │          │
              └──────────────┼──────────────┘──────────┘        
                      
                             │
                             ▼
                    Validator Agent
                             │
                             ▼
                   Review Writer Agent
                             │
                             ▼
                       Final Review
```

The key idea is:

> **Different review tasks require different repository context.**

The system therefore combines **multi agent specialization** with **agent specific RAG retrieval** rather than giving every agent the same context.

---

# 🧠 Agentic Architecture

The review pipeline contains **6 AI agents**.

### Parallel specialist agents

Four agents independently analyze the Pull Request:

| Agent                   | Focus                                                |
| ----------------------- | ---------------------------------------------------- |
| 🔍 **Quality Agent**    | Code quality, maintainability, and design issues     |
| 🔐 **Security Agent**   | Security vulnerabilities and unsafe patterns         |
| 🐛 **Bug Agent**        | Potential bugs, incorrect behavior, and logic issues |
| ⚡ **Performance Agent** | Performance bottlenecks and inefficient operations   |

These four agents execute **in parallel**.

### Sequential final stage agents

After the specialist agents finish:

| Agent                      | Responsibility                                                       |
| -------------------------- | -------------------------------------------------------------------- |
| ✅ **Validator Agent**      | Reviews and validates the findings produced by the specialist agents |
| 📝 **Review Writer Agent** | Produces the final structured review from the validated findings     |

Therefore:

```text
4 Parallel Agents
       │
       ▼
1 Validator Agent
       │
       ▼
1 Review Writer Agent
```

**Total: 6 AI agents.**

---

# 🎯 Agent Specific Context

One of the core design decisions of the system is that **each specialist agent receives context tailored to its review responsibility**.

The system does not simply retrieve a set of repository files and send the same information to every agent.

Instead:

```text
                       Repository
                           │
                           ▼
                    RAG Retrieval
                           │
             ┌─────────────┼──────────────────────────┐
             │             │             │            │                           
             ▼             ▼             ▼            ▼
         Quality       Security          Bug       Performance 
          Query         Query            Query        Query
             │             │             │             │
             ▼             ▼             ▼             ▼
         Quality       Security          Bug       Performance 
         Context       Context          Context       Context
             │             │             │             │
             └─────────────┼───────────────────────────┘
                        
```

For example, a Security Agent may need repository context related to authentication, authorization, validation, or data access, while a Performance Agent may benefit from database operations, loops, caching, and I/O-related code.

This allows retrieval to be **task oriented rather than generic**.

---

# 🔎 Changed Code + Supporting Repository Context

The review context is built from two major sources.

### Changed file context

The actual files modified by the Pull Request are included directly in the review context.

```text
Pull Request
     │
     ▼
Changed Files
     │
     ▼
Code Chunks
     │
     ▼
Changed File Context
```

### Supporting repository context

The system also retrieves relevant code from elsewhere in the repository.

```text
Repository
     │
     ▼
Related Files
     │
     ▼
Code Chunks
     │
     ▼
Agent Specific Retrieval
```

The final context therefore looks like:

```text
                 Agent Context
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
   Changed File Context    Supporting Context
                                   │
                                   ▼
                           Agent specific RAG
```

This is important because a changed function often cannot be reviewed correctly in isolation.

For example, a modified function may call another function whose behavior determines whether the change introduces a bug. Repository retrieval allows the relevant implementation or surrounding code to be provided to the Bug Agent.

---

# ⚙️ Review Execution

The LangGraph workflow orchestrates the review.

    ```text
                                 START
                                   │
                                   ▼
                            Review Context
                                   │
              ┌────────────────────|────────────────────     
              │              │              │          │   
              ▼              ▼              ▼          ▼
           Quality        Security          Bug     Performance
            Agent          Agent           Agent      Agent
              │              │              │          │
              └────────────────────|────────┘──────────┘        
                                   |
                             AGGREGATE
                                   │
                                   ▼
                          Validator Agent
                                   │
                                   ▼
                         Review Writer Agent
                                   │
                                   ▼
                                  END
```

The four specialist agents are independent review stages and can execute concurrently.

This reduces the latency that would occur if every specialist reviewer had to wait for the previous reviewer to finish.

---

# 🧩 Structured Findings

Each specialist agent produces **structured review findings** rather than only returning free-form text.

A finding can contain information such as:

```json
{
  "title": "Potential null reference",
  "description": "The returned value may be None before accessing name.",
  "severity": "high",
  "file": "service.py",
  "line": 42,
  "source_agents": ["bug"]
}
```

Structured findings make it possible to:

* Validate findings
* Track their source agent
* Aggregate findings
* Display findings consistently
* Add metadata
* Build additional processing stages

The review pipeline can therefore operate on structured data instead of relying entirely on generated prose.

---

# ✅ Validation Layer

The specialist agents are intentionally separated from the final review generation.

```text
Quality ──────┐
Security ─────┤
Bug ──────────┼──► Validator ──► Review Writer
Performance ──┘
```

The **Validator Agent** receives the specialist findings and performs a dedicated validation/consolidation step before the final review is written.

This creates a useful separation:

```text
Detection → Validation → Presentation
```

Rather than allowing potentially incorrect specialist findings to directly become the final review.

---

# 📝 Review Writer

The Review Writer is responsible for turning the validated findings into the final review response.

This separates:

**Finding generation**

from:

**Review composition**

```text
Specialist Analysis
        │
        ▼
Structured Findings
        │
        ▼
Validation
        │
        ▼
Validated Findings
        │
        ▼
Review Writer
        │
        ▼
Final Review
```

This makes the final response independent from the individual specialist agents' output format.

---

# 🤖 LLM Provider Abstraction

The application is designed to work with multiple LLM providers.

Currently supported providers include:

* OpenAI
* Google Gemini
* Groq
* Mistral
* Ollama

The LLM layer abstracts provider/model creation away from the agents.

This means the agents don't need to know how a specific provider is initialized.



---

# 🎛️ Agent Level Model Configuration

LLM configuration can be specified independently for different agents.

For example:

```text
Quality Agent       → Model A
Security Agent      → Model B
Bug Agent           → Model C
Performance Agent   → Model D
Validator Agent     → Model E
Review Writer       → Model F
```

This allows the system to experiment with different models based on:

* Reasoning capability
* Latency
* Cost
* Provider availability
* Local vs hosted execution

A lightweight model could potentially be used for a less demanding stage while a stronger reasoning model is reserved for validation.

---

# 🔄 End to End Pipeline

```text
1. User submits GitHub Pull Request
                    │
                    ▼
2. GitHubService fetches PR information
                    │
                    ▼
3. Changed files are identified
                    │
                    ▼
4. Repository context is prepared
                    │
                    ▼
5. Agent-specific RAG context is retrieved
                    │
                    ▼
6. Four specialist agents execute in parallel
                    │
┌───────────────────|────────────────────     
│              │              │          │   
▼              ▼              ▼          ▼
Quality     Security         Bug     Performance
Agent        Agent          Agent      Agent
│              │              │          │
└───────────────────|─────────┘──────────┘        
                    │
                    ▼
7. Specialist findings are aggregated
                    │
                    ▼
8. Validator Agent validates the findings
                    │
                    ▼
9. Review Writer generates final review
                    │
                    ▼
10. Final review is returned to the client
```

---

# 🌐 API & Async Execution

The backend is built with **FastAPI**.

The application supports both direct review execution and asynchronous review jobs.

For longer reviews, the system can start a review job and expose its progress through **Server Sent Events (SSE)**.

Conceptually:

```text
Client
  │
  │ Start Review
  ▼
Review Job
  │
  ├── RAG
  ├── Quality Agent
  ├── Security Agent
  ├── Bug Agent
  ├── Performance Agent
  ├── Validator
  └── Review Writer
          │
          ▼
      Final Review
```

The frontend can receive progress updates while the review is executing instead of waiting for a single long running request to complete.

---

# 🏗️ System Architecture

```text
┌───────────────────────────────────────┐
│               Frontend                │
│          React + TypeScript           │
└──────────────────┬────────────────────┘
                   │
                HTTP/SSE
                   │
                   ▼
┌───────────────────────────────────────┐
│                FastAPI                │
│               API Layer               │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│            ReviewService              │
│                                       │
│      Coordinates review execution     │
└───────────────┬───────────┬───────────┘
                │           │
                ▼           ▼
       ┌──────────────┐ ┌──────────────┐
       │ GitHubService│ │  RAGService  │
       └──────────────┘ └───────┬──────┘
                                │
                                ▼
                           ┌──────────┐
                           │ ChromaDB │
                           └──────────┘
                                │
                                ▼
                       Agent Specific Context
                                │
                                ▼
                       ┌──────────────────┐
                       │    ReviewGraph   │
                       │     LangGraph    │
                       └────────┬─────────┘
                                │
               
                        4 Specialized Agents
                                │
                                ▼
                         Validator Agent
                                │
                                ▼
                       Review Writer Agent
                                │
                                ▼
                           Final Review
```

---

# 📁 Project Structure

```text
pr-review-agent/
│
├── backend/
│   │
│   ├── agents/
│   │   ├── base.py
│   │   ├── bug_agent.py
│   │   ├── performance_agent.py
│   │   ├── quality_agent.py
│   │   ├── security_agent.py
│   │   ├── validator_agent.py
│   │   └── review_writer_agent.py
│   │
│   ├── api/
│   │   └── review.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── graph/
│   │   ├── review_graph.py
│   │   └── state.py
│   │
│   ├── llm/
│   │   ├── base.py
│   │   └── service.py
│   │
│   ├── models/
│   │   ├── agent.py
│   │   ├── api.py
│   │   ├── client_review.py
│   │   ├── finding.py
│   │   ├── pr.py
│   │   ├── rag.py
│   │   └── review.py
│   │
│   ├── services/
│   │   ├── github_service.py
│   │   ├── rag_service.py
│   │   ├── review_job.py
│   │   ├── review_service.py
│   │   └── rag/
│   │
│   ├── tests/
│   ├── utils/
│   ├── main.py
│   ├── pyproject.toml
│   └── requirements.txt
│
└── frontend/
    ├── src/
    ├── public/
    ├── package.json
    └── vite.config.ts
```

---

# 🛠️ Tech Stack

### Backend

* Python
* FastAPI
* Pydantic
* Uvicorn

### Agentic AI

* LangGraph
* LangChain
* Multi agent orchestration

### Retrieval

* ChromaDB
* Embeddings
* Repository code chunking
* Agent specific retrieval

### LLM Providers

* OpenAI
* Google Gemini
* Groq
* Mistral
* Ollama

### GitHub

* GitHub API
* Repository file retrieval
* Pull Request analysis

### Frontend

* React
* TypeScript
* Vite

### Real Time Communication

* Server Sent Events (SSE)

---

# 🚀 Getting Started

## Prerequisites

* Python 3.12+
* Node.js
* Git
* GitHub Personal Access Token
* API key for at least one supported LLM provider

## Clone

```bash
git clone https://github.com/yashkhatri012/pr-review-agent.git
cd pr-review-agent
```

---

## Backend Setup

```bash
cd backend
```

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Or:

```bash
uv sync
```

Create your environment file:

```text
.env
```

Use `.env.example` as the reference for the required configuration.

Run the backend:

```bash
uvicorn main:app --reload
```

API documentation:

```text
http://localhost:8000/docs
```

---

# 🖥️ Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

# 🧪 Testing

Run the backend tests:

```bash
pytest
```

For verbose output:

```bash
pytest -v
```

---

# ⚙️ Configuration

Configuration is centralized in:

```text
backend/config/settings.py
```

The application supports configuration for:

* LLM providers
* LLM models
* API keys
* GitHub integration
* RAG
* ChromaDB
* Application settings

The provider/model abstraction allows the underlying LLM configuration to be changed without modifying the individual review agents.

---

# 🔮 Roadmap

Potential areas for future development:

* [ ] Improve agent-specific retrieval
* [ ] Better code-aware chunking
* [ ] Finding deduplication
* [ ] Review evaluation and benchmarking
* [ ] Confidence scoring
* [ ] Better agent failure handling
* [ ] Token and cost tracking
* [ ] Production observability
* [ ] Persistent review history
* [ ] Incremental repository indexing
* [ ] GitHub webhook-based reviews
* [ ] Inline GitHub review comments
* [ ] Additional specialist agents
* [ ] Improved local LLM support

## 📚 References & Inspiration

The architecture of llms was inspired by:
[Repository](https://github.com/FareedKhan-dev/production-grade-agentic-system)
[Article](https://levelup.gitconnected.com/building-the-7-layers-of-a-production-grade-agentic-ai-system-37ee5d941f1c)
