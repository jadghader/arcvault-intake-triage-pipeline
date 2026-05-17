import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StepProgress } from "../components/StepProgress";
import type { StepEvent } from "../types/index";

const INGESTION_DONE: StepEvent = {
  step: 1,
  name: "ingestion",
  status: "done",
  data: { id: "msg_001", source: "Web Form" },
};

const CLASSIFICATION_RUNNING: StepEvent = {
  step: 2,
  name: "classification",
  status: "running",
};

const CLASSIFICATION_DONE: StepEvent = {
  step: 2,
  name: "classification",
  status: "done",
  data: { category: "Bug Report", priority: "High", confidence_score: 0.94 },
};

const ROUTING_DONE_ESCALATED: StepEvent = {
  step: 4,
  name: "routing",
  status: "done",
  data: {
    destination_queue: "Escalation",
    escalation_flag: true,
    escalation_reason: "Billing discrepancy $260 exceeds $200 threshold",
  },
};

const ROUTING_DONE_STANDARD: StepEvent = {
  step: 4,
  name: "routing",
  status: "done",
  data: { destination_queue: "Engineering", escalation_flag: false },
};

const STEP_ERROR: StepEvent = {
  step: 2,
  name: "classification",
  status: "error",
  error: "API timeout",
};

describe("StepProgress", () => {
  it("renders nothing when steps array is empty", () => {
    const { container } = render(<StepProgress steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders step labels", () => {
    render(<StepProgress steps={[INGESTION_DONE]} />);
    expect(screen.getByText("Ingestion")).toBeInTheDocument();
  });

  it("shows Processing text while a step is running", () => {
    render(<StepProgress steps={[CLASSIFICATION_RUNNING]} />);
    expect(screen.getByText("Processing…")).toBeInTheDocument();
  });

  it("renders classification data after completion", () => {
    render(<StepProgress steps={[CLASSIFICATION_DONE]} />);
    expect(screen.getByText("Bug Report")).toBeInTheDocument();
    expect(screen.getByText(/94%/)).toBeInTheDocument();
  });

  it("shows escalation badge for escalated routing", () => {
    render(<StepProgress steps={[ROUTING_DONE_ESCALATED]} />);
    expect(screen.getByText("Escalated")).toBeInTheDocument();
  });

  it("shows escalation reason text", () => {
    render(<StepProgress steps={[ROUTING_DONE_ESCALATED]} />);
    expect(screen.getByText(/Billing discrepancy/)).toBeInTheDocument();
  });

  it("does NOT show escalation badge for standard routing", () => {
    render(<StepProgress steps={[ROUTING_DONE_STANDARD]} />);
    expect(screen.queryByText("Escalated")).not.toBeInTheDocument();
  });

  it("shows error message when a step errors", () => {
    render(<StepProgress steps={[STEP_ERROR]} />);
    expect(screen.getByText("API timeout")).toBeInTheDocument();
  });

  it("renders multiple steps", () => {
    render(<StepProgress steps={[INGESTION_DONE, CLASSIFICATION_DONE, ROUTING_DONE_STANDARD]} />);
    expect(screen.getByText("Ingestion")).toBeInTheDocument();
    expect(screen.getByText("Classification")).toBeInTheDocument();
    expect(screen.getByText("Routing & Escalation")).toBeInTheDocument();
  });
});
