# WebSockets — live batch progress

The one place a WebSocket genuinely earns its place: a scanned newspaper
PDF can take a minute of OCR + classification, and a live
`processed / total` count beats a spinner.

## Flow

```
POST /api/batch/jobs        (multipart file, mode)   -> 202 {job_id, state:"pending", ...}
WS   /api/batch/jobs/{id}/ws?token=<access_jwt>       -> stream of BatchJobStatus snapshots
GET  /api/batch/jobs/{id}                             -> one snapshot (polling fallback)
```

`BatchJobStatus` = `{job_id, state, processed, total, error, result}` where
`state ∈ pending | running | complete | error` and `result` (a
`BatchResponse`) is populated only when `state == "complete"`.

## Server (`app/jobs.py`, `routers/batch_jobs.py`)

- `POST /jobs` creates an in-memory `BatchJob`, launches
  `asyncio.create_task(run_batch_job(...))` (task kept in a module-level set
  so the GC can't cancel it), returns immediately.
- `run_batch_job` parses the file off the event loop
  (`asyncio.to_thread`), then classifies each row with `to_thread`, calling
  `job.publish()` after every row. Predictions are persisted in one batch
  at the end.
- Each WS connection `job.subscribe()`s an `asyncio.Queue`; `publish()`
  fan-outs the snapshot to all queues. A 90 s `wait_for` timeout emits a
  `{"type":"keepalive"}` frame so idle proxies don't drop the socket.
- **Auth**: browsers can't set `Authorization` on a WebSocket, so the
  access token is a `?token=` query param, validated with
  `decode_access_token`. Bad/missing token or wrong owner → `close(4404)`.

## Client (`frontend/src/lib/batchJob.ts`)

`runBatchJob(file, onProgress)`:
1. `POST /batch/jobs`.
2. Open the WS; on each snapshot call `onProgress({state, processed, total})`;
   resolve on a terminal state.
3. If the socket errors or closes early, fall back to polling `GET` every
   500 ms.

The batch page renders a progress bar from `processed / total`.

## Limitations

Jobs are process-local and un-persisted — fine for a single instance. A
multi-worker deployment would move the job store to Redis / a real queue;
the API shape is designed to contain that change.

## Tests

`backend/tests/test_batch_jobs.py` drives the job to completion via both
polling and a real `TestClient.websocket_connect`, and checks the `4404`
rejection for a bad token and ownership isolation.
