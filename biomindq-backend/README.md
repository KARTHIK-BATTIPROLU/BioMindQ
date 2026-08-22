# BioMindQ — Biomedical Research Intelligence Backend

BioMindQ is an asynchronous FastAPI backend for biomedical research intelligence. It answers research questions by retrieving live data from real biomedical databases (PubMed, ChEMBL, PubChem, DrugBank), cross-verifying evidence across sources, and generating structured responses that separate **retrieved evidence** from **AI-generated summaries**.

---

## Architecture Overview

1. **Planner (`llama-3.1-8b-instant`)**: Analyzes research questions and formulates source-specific queries.
2. **Parallel Retrieval Engine**: Concurrently queries PubMed (NCBI E-utilities), ChEMBL REST, PubChem PUG REST, and DrugBank (gated) via `asyncio.gather`.
3. **Verifier (`llama-3.1-8b-instant`)**: Performs entity resolution, cross-source agreement detection, dynamic conflict reasoning, and confidence scoring.
4. **Answer Generator (`llama-3.3-70b-versatile`)**: Produces structured output separating retrieved evidence (with URLs and claims) from AI summary synthesis.
5. **Persistence**: Saves query history and latency metrics to MongoDB (`queries` and `source_health` collections).

---

## Required Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```bash
MONGODB_URI=mongodb://localhost:27017
GROQ_API_KEY=your_groq_api_key_here
NCBI_API_KEY=        # Optional — raises PubMed rate limit from 3 to 10 req/sec
DRUGBANK_API_KEY=    # Optional — leave blank; system auto-activates DrugBank when key is set
```

---

## Local Development & Setup

### 1. Install Dependencies

```bash
cd biomindq-backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Base: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Check: `GET http://localhost:8000/api/health`
- Research Query: `POST http://localhost:8000/api/query`

### 3. Run Test Suite

```bash
python -m pytest -s tests/
```

---

## Render Deployment Guide

### Build & Start Commands

- **Environment**: Python 3.11+
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Environment Variables on Render
Set the following keys under Render Web Service -> Environment:
- `MONGODB_URI`
- `GROQ_API_KEY`
- `NCBI_API_KEY` (Optional)
- `DRUGBANK_API_KEY` (Optional)
