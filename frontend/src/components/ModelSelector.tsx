import { useQuery } from "@tanstack/react-query";
import type { AvailableModels } from "../types";

async function fetchModels(): Promise<AvailableModels> {
  const res = await fetch("/api/models");
  if (!res.ok) throw new Error("Failed to load models");
  return res.json();
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  groq: "Groq",
  mistral: "Mistral",
  ollama: "Ollama (local)",
};

interface Props {
  value: string;
  onChange: (model: string) => void;
}

export function ModelSelector({ value, onChange }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: fetchModels,
    staleTime: 60_000,
  });

  if (isLoading) {
    return <div className="h-9 w-48 animate-pulse rounded-md bg-gray-200" />;
  }

  const available = data?.available ?? {};
  const hasModels = Object.keys(available).length > 0;

  if (!hasModels) {
    return (
      <div className="text-sm text-red-600">
        No API keys configured — add keys to <code>.env</code>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-600">Model</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
      >
        {Object.entries(available).map(([provider, models]) => (
          <optgroup key={provider} label={PROVIDER_LABELS[provider] ?? provider}>
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
