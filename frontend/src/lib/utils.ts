import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString();
}

export const PRIORITY_COLORS: Record<string, string> = {
  High: "bg-red-100 text-red-700",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-green-100 text-green-700",
};

export const QUEUE_COLORS: Record<string, string> = {
  Engineering: "bg-blue-100 text-blue-700",
  Product: "bg-purple-100 text-purple-700",
  Billing: "bg-emerald-100 text-emerald-700",
  "IT / Security": "bg-orange-100 text-orange-700",
  Escalation: "bg-red-100 text-red-700",
};
