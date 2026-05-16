import { useState } from "react";
import { Send, RotateCcw } from "lucide-react";
import { ModelSelector } from "../components/ModelSelector";
import { StepProgress } from "../components/StepProgress";
import { ResultCard } from "../components/ResultCard";
import { usePipelineRun } from "../hooks/usePipelineRun";

const SOURCES = ["Email", "Web Form", "Support Portal", "Other"];

const SAMPLE_MESSAGES = [
  { label: "Login 403 error", value: "Hi, I tried logging in this morning and keep getting a 403 error. My account is arcvault.io/user/jsmith. This started after your update last Tuesday." },
  { label: "Bulk export feature request", value: "We'd love to see a bulk export feature for our audit logs. We're a compliance-heavy org and this would save us hours every month." },
  { label: "Invoice overcharge", value: "Invoice #8821 shows a charge of $1,240 but our contract rate is $980/month. Can someone look into this?" },
  { label: "SSO / Okta question", value: "Is there a way to set up SSO with Okta? We're evaluating switching our auth provider." },
  { label: "Outage — multiple users", value: "Your dashboard stopped loading for us around 2pm EST. Checked our end — it's definitely on yours. Multiple users affected." },
];

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
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Run Pipeline</h1>
        <p className="mt-1 text-sm text-gray-500">
          Submit a customer message and watch it flow through all 6 pipeline steps in real time.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        {/* Sample messages */}
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            Quick samples
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            {SAMPLE_MESSAGES.map((s) => (
              <button
                key={s.label}
                type="button"
                onClick={() => setMessage(s.value)}
                className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-600 hover:bg-gray-100 transition-colors"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Message input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Customer Message
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
            placeholder="Paste or type the customer message here…"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={running}
          />
        </div>

        {/* Source + Model row */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-600">Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              disabled={running}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {SOURCES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <ModelSelector value={model} onChange={setModel} />
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-1">
          <button
            type="submit"
            disabled={running || !message.trim()}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
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
          {(steps.length > 0 || result) && (
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-2 rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {steps.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
            Pipeline Steps
          </h2>
          <StepProgress steps={steps} />
        </div>
      )}

      {result && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
            Processed Record
          </h2>
          <ResultCard record={result} />
        </div>
      )}
    </div>
  );
}
