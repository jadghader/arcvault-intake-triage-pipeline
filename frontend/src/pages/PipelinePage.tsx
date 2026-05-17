import { useState } from "react";
import { Send, RotateCcw } from "lucide-react";
import { ModelSelector } from "../components/ModelSelector";
import { StepProgress } from "../components/StepProgress";
import { ResultCard } from "../components/ResultCard";
import { usePipelineRun } from "../hooks/usePipelineRun";

const SOURCES = ["Email", "Web Form", "Support Portal", "Other"];

const SAMPLE_MESSAGES = [
  {
    label: "Login 403 error",
    tag: "Bug",
    value:
      "Hi, I tried logging in this morning and keep getting a 403 error. My account is arcvault.io/user/jsmith. This started after your update last Tuesday.",
  },
  {
    label: "Bulk export request",
    tag: "Feature",
    value:
      "We'd love to see a bulk export feature for our audit logs. We're a compliance-heavy org and this would save us hours every month.",
  },
  {
    label: "Invoice overcharge",
    tag: "Billing",
    value:
      "Invoice #8821 shows a charge of $1,240 but our contract rate is $980/month. Can someone look into this?",
  },
  {
    label: "SSO / Okta setup",
    tag: "Tech",
    value: "Is there a way to set up SSO with Okta? We're evaluating switching our auth provider.",
  },
  {
    label: "Outage — multiple users",
    tag: "Incident",
    value:
      "Your dashboard stopped loading for us around 2pm EST. Checked our end — it's definitely on yours. Multiple users affected.",
  },
];

const TAG_COLORS: Record<string, string> = {
  Bug: "bg-rose-50 text-rose-600 border-rose-200",
  Feature: "bg-violet-50 text-violet-600 border-violet-200",
  Billing: "bg-amber-50 text-amber-600 border-amber-200",
  Tech: "bg-sky-50 text-sky-600 border-sky-200",
  Incident: "bg-red-50 text-red-700 border-red-200",
};

export function PipelinePage() {
  const [message, setMessage] = useState("");
  const [source, setSource] = useState("Web Form");
  const [model, setModel] = useState("claude-sonnet-4-6");
  const { run, reset, steps, result, running, error } = usePipelineRun();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    run({ raw_message: message, source, model });
  };

  const handleReset = () => {
    reset();
    setMessage("");
  };

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Run Pipeline</h1>
        <p className="mt-1 text-sm text-slate-500">
          Submit a customer message and watch it flow through all 6 pipeline steps in real time.
        </p>
      </div>

      {/* Input form */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Sample messages */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Try a sample message
            </p>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_MESSAGES.map((s) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => setMessage(s.value)}
                  disabled={running}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:bg-white disabled:opacity-40"
                >
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${TAG_COLORS[s.tag] ?? "bg-slate-100 text-slate-500 border-slate-200"}`}
                  >
                    {s.tag}
                  </span>
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <hr className="border-slate-100" />

          {/* Message textarea */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Customer Message
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              placeholder="Paste or type the customer message here…"
              disabled={running}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm leading-relaxed shadow-sm placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-50 disabled:text-slate-400 transition"
            />
          </div>

          {/* Source + Model + Actions row */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-600">Source</label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                disabled={running}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:opacity-50"
              >
                {SOURCES.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>

            <ModelSelector value={model} onChange={setModel} />

            <div className="ml-auto flex gap-2">
              {(steps.length > 0 || result) && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Reset
                </button>
              )}
              <button
                type="submit"
                disabled={running || !message.trim()}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                {running ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Running…
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Run Pipeline
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Pipeline steps */}
      {steps.length > 0 && (
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Pipeline Steps
          </p>
          <StepProgress steps={steps} />
        </div>
      )}

      {/* Result */}
      {result && (
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Processed Record
          </p>
          <ResultCard record={result} />
        </div>
      )}
    </div>
  );
}
