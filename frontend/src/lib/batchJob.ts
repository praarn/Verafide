import { api, tokenStore, wsOrigin } from "./api";
import type { BatchJobStatus } from "./types";

export interface BatchProgress {
  state: BatchJobStatus["state"];
  processed: number;
  total: number;
}

/**
 * Starts a batch job, then streams progress over a WebSocket. Falls back to
 * HTTP polling if the socket can't be established. Resolves with the final
 * BatchJobStatus (state "complete" or "error").
 */
export async function runBatchJob(
  file: File,
  onProgress: (p: BatchProgress) => void,
): Promise<BatchJobStatus> {
  const fd = new FormData();
  fd.append("file", file);
  const { data: started } = await api.post<BatchJobStatus>("/batch/jobs", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  const jobId = started.job_id;
  onProgress({ state: started.state, processed: 0, total: started.total });

  try {
    return await streamViaWs(jobId, onProgress);
  } catch {
    return await pollViaHttp(jobId, onProgress);
  }
}

function streamViaWs(
  jobId: string,
  onProgress: (p: BatchProgress) => void,
): Promise<BatchJobStatus> {
  return new Promise((resolve, reject) => {
    const token = tokenStore.access();
    const ws = new WebSocket(`${wsOrigin()}/api/batch/jobs/${jobId}/ws?token=${token}`);
    let settled = false;

    const finish = (fn: () => void) => {
      settled = true;
      try {
        ws.close();
      } catch {
        /* noop */
      }
      fn();
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "keepalive") return;
      onProgress({ state: msg.state, processed: msg.processed, total: msg.total });
      if (msg.state === "complete" || msg.state === "error") {
        finish(() => resolve(msg as BatchJobStatus));
      }
    };
    ws.onerror = () => {
      if (!settled) reject(new Error("websocket error"));
    };
    ws.onclose = () => {
      if (!settled) reject(new Error("websocket closed early"));
    };
  });
}

async function pollViaHttp(
  jobId: string,
  onProgress: (p: BatchProgress) => void,
): Promise<BatchJobStatus> {
  for (let i = 0; i < 600; i++) {
    const { data } = await api.get<BatchJobStatus>(`/batch/jobs/${jobId}`);
    onProgress({ state: data.state, processed: data.processed, total: data.total });
    if (data.state === "complete" || data.state === "error") return data;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Batch job timed out.");
}
