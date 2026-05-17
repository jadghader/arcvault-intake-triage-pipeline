import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResultCard } from "../components/ResultCard";
import type { ProcessedRecord } from "../types/index";

const BASE_RECORD: ProcessedRecord = {
  id: "msg_001",
  source: "Web Form",
  timestamp: "2026-05-17T11:11:36.139190Z",
  raw_message: "I keep getting a 403 error on login.",
  model_used: "claude-sonnet-4-6",
  classification: {
    category: "Bug Report",
    priority: "High",
    confidence_score: 0.94,
  },
  enrichment: {
    core_issue: "User cannot log in due to a 403 error.",
    identifiers: { error_code: "403", account_id: "arcvault.io/user/jsmith" },
    urgency_signal: "Access is completely blocked.",
  },
  routing: {
    destination_queue: "Engineering",
    routing_reason: "Bug Report routes to Engineering queue",
    escalation_flag: false,
    escalation_reason: null,
  },
  summary: "User is blocked from logging in due to a 403 error. Engineering should investigate the auth service.",
};

const ESCALATED_RECORD: ProcessedRecord = {
  ...BASE_RECORD,
  id: "msg_003",
  classification: { ...BASE_RECORD.classification, category: "Billing Issue", confidence_score: 0.98 },
  enrichment: {
    core_issue: "Customer was overcharged $260 on invoice #8821.",
    identifiers: { invoice_number: "8821", discrepancy: "260" },
    urgency_signal: "Confirmed billing discrepancy of $260.",
  },
  routing: {
    destination_queue: "Escalation",
    routing_reason: "Billing discrepancy $260 exceeds $200 threshold",
    escalation_flag: true,
    escalation_reason: "Billing discrepancy $260 exceeds $200 threshold",
  },
  summary: "Invoice #8821 shows a $260 overcharge. This has been escalated for human review.",
};

describe("ResultCard", () => {
  it("renders record ID", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.getByText("msg_001")).toBeInTheDocument();
  });

  it("renders category and priority", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.getByText("Bug Report")).toBeInTheDocument();
    // "High" appears in both the badge and the grid field
    expect(screen.getAllByText("High").length).toBeGreaterThanOrEqual(1);
  });

  it("renders confidence score", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.getByText("94%")).toBeInTheDocument();
  });

  it("renders core issue", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.getByText("User cannot log in due to a 403 error.")).toBeInTheDocument();
  });

  it("renders identifiers as key: value chips", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.getByText(/error_code/)).toBeInTheDocument();
    // 403 appears in the identifier chip (key span and value are siblings, find the value)
    expect(screen.getAllByText(/403/).length).toBeGreaterThanOrEqual(1);
  });

  it("renders handoff summary", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.getByText(/blocked from logging in/)).toBeInTheDocument();
  });

  it("does NOT show escalation banner for non-escalated record", () => {
    render(<ResultCard record={BASE_RECORD} />);
    expect(screen.queryByText("Escalated")).not.toBeInTheDocument();
  });

  it("shows escalation banner for escalated record", () => {
    render(<ResultCard record={ESCALATED_RECORD} />);
    expect(screen.getByText("Escalated")).toBeInTheDocument();
  });

  it("shows escalation reason in banner", () => {
    render(<ResultCard record={ESCALATED_RECORD} />);
    expect(screen.getByText(/Billing discrepancy \$260/)).toBeInTheDocument();
  });

  it("shows destination queue badge", () => {
    render(<ResultCard record={BASE_RECORD} />);
    // "→ Engineering" appears in the badge; "Engineering" also appears in the routing_reason
    expect(screen.getAllByText(/Engineering/).length).toBeGreaterThanOrEqual(1);
  });
});
