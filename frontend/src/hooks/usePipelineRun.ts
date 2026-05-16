import { useState, useCallback } from "react";
import type { StepEvent, ProcessedRecord } from "../types";

interface RunPayload {
  raw_message: string;
  source: string;
  model: string;
}

const STEP_NAMES = ["ingestion", "classification", "enrichment", "routing", "summary"];

function initSteps(): StepEvent[] {
  return STEP_NAMES.map((name, i) => ({
    step: i + 1,
    name,
    status: "running" as const,
    data: null,
  }));
}

export function usePipelineRun() {
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [result, setResult] = useState<ProcessedRecord | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (payload: RunPayload) => {
    setRunning(true);
    setError(null);
    setResult(null);
    setSteps(initSteps().map((s) => ({ ...s, status: "running" as const })));

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event: StepEvent = JSON.parse(line.slice(6));

            if (event.name === "complete") {
              setResult(event.data as unknown as ProcessedRecord);
            } else {
              setSteps((prev) =>
                prev.map((s) => (s.name === event.name ? event : s))
              );
            }
          } catch {
            // malformed line — skip
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRunning(false);
    }
  }, []);

  const reset = useCallback(() => {
    setSteps([]);
    setResult(null);
    setError(null);
  }, []);

  return { run, reset, steps, result, running, error };
}
