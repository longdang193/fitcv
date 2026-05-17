# Reproduction Steps

1. Start stack: docker compose up -d --build redis web worker
2. POST http://localhost:8000/runs with sample payload.
3. Observe run terminal succeeded but trace degraded.
4. GET /admin/runs/<run_id>/agentic-live-trace.json and confirm 401 invalid_api_key.

