import { describe, it, expect } from "vitest";
import { formatConfidence, formatTimestamp, PRIORITY_COLORS, QUEUE_COLORS } from "../lib/utils";

describe("formatConfidence", () => {
  it("converts 0.98 to 98%", () => {
    expect(formatConfidence(0.98)).toBe("98%");
  });

  it("rounds 0.725 to 73%", () => {
    expect(formatConfidence(0.725)).toBe("73%");
  });

  it("handles 0", () => {
    expect(formatConfidence(0)).toBe("0%");
  });

  it("handles 1", () => {
    expect(formatConfidence(1)).toBe("100%");
  });
});

describe("formatTimestamp", () => {
  it("returns a non-empty string for a valid ISO timestamp", () => {
    const result = formatTimestamp("2026-05-17T11:11:36.139190Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("PRIORITY_COLORS", () => {
  it("has entries for all three priority levels", () => {
    expect(PRIORITY_COLORS["High"]).toBeDefined();
    expect(PRIORITY_COLORS["Medium"]).toBeDefined();
    expect(PRIORITY_COLORS["Low"]).toBeDefined();
  });
});

describe("QUEUE_COLORS", () => {
  it("has entries for all standard queues", () => {
    expect(QUEUE_COLORS["Engineering"]).toBeDefined();
    expect(QUEUE_COLORS["Product"]).toBeDefined();
    expect(QUEUE_COLORS["Billing"]).toBeDefined();
    expect(QUEUE_COLORS["IT / Security"]).toBeDefined();
    expect(QUEUE_COLORS["Escalation"]).toBeDefined();
  });
});
