# Web3 Sybil Detection API

FastAPI backend and Modal GPU worker for Module 1 of a Web3 Sybil Detection dashboard.
The API starts asynchronous discovery jobs, polls task status, and returns graph data (`nodes` + `links`) for frontend visualization.

## What this project does

- Exposes HTTP endpoints for Sybil discovery workflows.
- Uses Modal Serverless GPU to run the AI pipeline asynchronously (`.spawn()`).
- Returns task status in a polling-friendly format: `PROCESSING`, `COMPLETED`, `FAILED`.
- Provides mock fallback behavior when Modal is not deployed yet, so frontend integration can continue.

## Tech Stack

- Python 3.11+ (project currently runs on newer Python versions too)
- FastAPI + Pydantic
- Modal (serverless compute)
- NetworkX, Scikit-learn
- PyTorch + PyTorch Geometric (in Modal worker image)

## Project Structure

```text
.
├── app/
│   ├── api/v1/endpoints/sybil.py      # REST endpoints
│   ├── schemas/sybil.py               # Request/response contracts
│   ├── services/sybil_service.py      # Modal spawn + polling logic
│   └── main.py                        # FastAPI entrypoint
├── modal_worker/
│   └── app.py                         # Modal App + GPU pipeline function
├── requirements.txt
└── .env.example
```

## API Contract (Module 1)

- `POST /api/v1/sybil/discovery/start`
  - Body: `DiscoveryRequest`
  - Returns: `DiscoveryStatusResponse` with `task_id`
- `GET /api/v1/sybil/discovery/status/{task_id}`
  - Returns: `DiscoveryStatusResponse` including `graph_data` when completed

## Quick Start

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment

```bash
cp .env.example .env
```

Fill in Modal credentials in `.env`:

```env
MODAL_TOKEN_ID=your_modal_token_id
MODAL_TOKEN_SECRET=your_modal_token_secret
```

> [!NOTE]
> The backend can still run without a deployed Modal app. In that case it falls back to mock task IDs/data for integration testing.

### 3) Run FastAPI

```bash
uvicorn app.main:app --reload
```

API base URL: `http://127.0.0.1:8000`

## Deploy the Modal Worker

The backend expects Modal app name `sybil-discovery-engine` and function `train_gae_pipeline`.

```bash
modal deploy modal_worker/app.py
```

After deployment, `start_discovery` will call:

- `modal.Function.lookup("sybil-discovery-engine", "train_gae_pipeline")`
- `modal_func.spawn(payload)`

## End-to-End Test Flow

### Start discovery job

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/sybil/discovery/start" \
  -H "Content-Type: application/json" \
  -d '{
    "time_range": {
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    },
    "max_nodes": 2000
  }'
```

### Poll status

```bash
curl "http://127.0.0.1:8000/api/v1/sybil/discovery/status/<task_id>"
```

## Behavior Notes

- `PROCESSING`: Modal job is still running (`TimeoutError` during `call.get(timeout=0)`).
- `COMPLETED`: `graph_data` is returned in `nodes` / `links` format.
- `FAILED`: worker error or invalid task id (message included).
- Mock task IDs (`"mock"` in `task_id`) return deterministic sample graph data for UI testing.

## Current Scope

This repository contains the Module 1 skeleton pipeline:

- Dummy graph generation with NetworkX
- Embedding simulation and KMeans clustering in Modal worker
- Backend-ready graph JSON response for dashboard rendering

It is designed as a foundation for replacing dummy logic with real GAE training and on-chain feature engineering.

