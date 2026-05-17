import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import type { StepEvent } from "../types";
import { cn } from "../lib/utils";

const STEP_LABELS: Record<string, string> = {
  ingestion: "Ingestion",
  classification: "Classification",
  enrichment: "Enrichment",
  routing: "Routing & Escalation",
  summary: "Summary Generation",
};

const STEP_DESCRIPTIONS: Record<string, string> = {
  ingestion: "Assigns ID, timestamp, normalises source",
  classification: "LLM → category, priority, confidence score",
  enrichment: "LLM → core issue, identifiers, urgency signal",
  routing: "Maps category → queue, applies escalation rules",
  summary: "LLM → 2–3 sentence handoff note",
};

function StepIcon({ status }: { status: StepEvent["status"] }) {
  if (status === "done") return <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500 flex-shrink-0" style={{ width: 18, height: 18 }} />;
  if (status === "error") return <AlertCircle className="flex-shrink-0 text-red-500" style={{ width: 18, height: 18 }} />;
  if (status === "running") return <Loader2 className="animate-spin flex-shrink-0 text-indigo-500" style={{ width: 18, height: 18 }} />;
  return (
    <div className="flex-shrink-0 rounded-full border-2 border-slate-200 bg-white" style={{ width: 18, height: 18 }} />
  );
}

function ClassificationDetail({ data }: { data: Record<string, unknown> }) {
  const category = data.category as string | undefined;
  const priority = data.priority as string | undefined;
  const score = data.confidence_score as number | undefined;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
      {category && (
        <span className="rounded-md bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700">
          {category}
        </span>
      )}
      {priority && (
        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600">
          Priority: {priority}
        </span>
      )}
      {score !== undefined && (
        <span className={cn(
          "rounded-md px-2 py-0.5",
          score >= 0.7 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
        )}>
          Confidence: {Math.round(score * 100)}%
        </span>
      )}
    </div>
  );
}

function RoutingDetail({ data }: { data: Record<string, unknown> }) {
  const queue = data.destination_queue as string | undefined;
  const escalated = data.escalation_flag as boolean | undefined;
  const reason = data.escalation_reason as string | undefined;
  return (
    <div className="mt-2 space-y-1">
      <div className="flex flex-wrap gap-1.5 text-xs">
        {queue && (
          <span className={cn(
            "rounded-md px-2 py-0.5 font-medium",
            escalated ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
          )}>
            → {queue}
          </span>
        )}
        {escalated && (
          <span className="rounded-md bg-red-100 px-2 py-0.5 font-semibold text-red-700">
            Escalated
          </span>
        )}
      </div>
      {escalated && reason && (
        <p className="text-xs text-red-600">{reason}</p>
      )}
    </div>
  );
}

function StepDetail({ step }: { step: StepEvent }) {
  if (!step.data || step.status !== "done") return null;
  if (step.name === "classification") return <ClassificationDetail data={step.data} />;
  if (step.name === "routing") return <RoutingDetail data={step.data} />;
  return null;
}

interface Props {
  steps: StepEvent[];
}

export function StepProgress({ steps }: Props) {
  if (steps.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {steps.map((step, i) => (
        <div
          key={step.name}
          className={cn(
            "flex gap-4 px-5 py-4 transition-colors",
            i > 0 && "border-t border-slate-100",
            step.status === "running" && "bg-indigo-50/60",
            step.status === "error" && "bg-red-50/60"
          )}
        >
          {/* Step number + icon */}
          <div className="flex flex-col items-center gap-1 pt-0.5">
            <StepIcon status={step.status} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={cn(
                "text-sm font-medium",
                step.status === "done" && "text-slate-800",
                step.status === "running" && "text-indigo-700",
                step.status === "error" && "text-red-700",
                step.status === "pending" && "text-slate-400",
              )}>
                {STEP_LABELS[step.name] ?? step.name}
              </span>
              {step.status === "running" && (
                <span className="text-xs font-medium text-indigo-500">Processing…</span>
              )}
              {step.error && (
                <span className="text-xs text-red-600">{step.error}</span>
              )}
            </div>
            {step.status !== "running" && step.status !== "error" && (
              <p className="text-xs text-slate-400 mt-0.5">
                {STEP_DESCRIPTIONS[step.name]}
              </p>
            )}
            <StepDetail step={step} />
          </div>
        </div>
      ))}
    </div>
  );
}
