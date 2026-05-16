import { CheckCircle, Circle, AlertCircle, Loader2 } from "lucide-react";
import type { StepEvent } from "../types";
import { cn } from "../lib/utils";

const STEP_LABELS: Record<string, string> = {
  ingestion: "Ingestion",
  classification: "Classification",
  enrichment: "Enrichment",
  routing: "Routing & Escalation",
  summary: "Summary Generation",
};

function StepIcon({ status }: { status: StepEvent["status"] }) {
  if (status === "done") return <CheckCircle className="h-5 w-5 text-green-500" />;
  if (status === "error") return <AlertCircle className="h-5 w-5 text-red-500" />;
  if (status === "running") return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
  return <Circle className="h-5 w-5 text-gray-300" />;
}

function StepDetail({ step }: { step: StepEvent }) {
  if (!step.data) return null;

  if (step.name === "classification") {
    const d = step.data as { category?: string; priority?: string; confidence_score?: number };
    return (
      <div className="mt-1 flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-700">{d.category}</span>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-600">Priority: {d.priority}</span>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-600">
          Confidence: {Math.round((d.confidence_score ?? 0) * 100)}%
        </span>
      </div>
    );
  }

  if (step.name === "routing") {
    const d = step.data as { destination_queue?: string; escalation_flag?: boolean };
    return (
      <div className="mt-1 flex flex-wrap gap-2 text-xs">
        <span className={cn(
          "rounded px-2 py-0.5",
          d.escalation_flag ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"
        )}>
          → {d.destination_queue}
        </span>
        {d.escalation_flag && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-red-600">Escalated</span>
        )}
      </div>
    );
  }

  return null;
}

interface Props {
  steps: StepEvent[];
}

export function StepProgress({ steps }: Props) {
  if (steps.length === 0) return null;

  return (
    <div className="space-y-2">
      {steps.map((step) => (
        <div
          key={step.name}
          className={cn(
            "flex flex-col rounded-lg border px-4 py-3 transition-all",
            step.status === "done" && "border-green-200 bg-green-50",
            step.status === "running" && "border-blue-200 bg-blue-50",
            step.status === "error" && "border-red-200 bg-red-50"
          )}
        >
          <div className="flex items-center gap-3">
            <StepIcon status={step.status} />
            <span className="text-sm font-medium text-gray-800">
              {STEP_LABELS[step.name] ?? step.name}
            </span>
            {step.status === "running" && (
              <span className="text-xs text-blue-500">Processing…</span>
            )}
            {step.error && (
              <span className="text-xs text-red-600">{step.error}</span>
            )}
          </div>
          <StepDetail step={step} />
        </div>
      ))}
    </div>
  );
}
