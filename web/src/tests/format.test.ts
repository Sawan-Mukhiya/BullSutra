import { describe, it, expect } from "vitest";
import {
  fmtPct,
  fmtSignedPct,
  fmtNum,
  fmtScore,
  fmtNpr,
  fmtVolume,
  fmtDate,
} from "../lib/format";

describe("format.ts helper functions", () => {
  it("handles null, undefined and NaN safely with em-dash", () => {
    expect(fmtPct(null)).toBe("—");
    expect(fmtPct(undefined)).toBe("—");
    expect(fmtPct(NaN)).toBe("—");

    expect(fmtSignedPct(null)).toBe("—");
    expect(fmtNum(null)).toBe("—");
    expect(fmtScore(null)).toBe("—");
    expect(fmtNpr(null)).toBe("—");
    expect(fmtVolume(null)).toBe("—");
    expect(fmtDate(null)).toBe("—");
  });

  it("formats percentages accurately", () => {
    expect(fmtPct(0.1234)).toBe("12.3%");
    expect(fmtPct(0.1234, 2)).toBe("12.34%");
    expect(fmtPct(0)).toBe("0.0%");
  });

  it("formats signed percentages with true minus symbol", () => {
    expect(fmtSignedPct(0.052)).toBe("+0.05%");
    expect(fmtSignedPct(5.2)).toBe("+5.20%");
    expect(fmtSignedPct(-3.45)).toBe("−3.45%");
    expect(fmtSignedPct(0)).toBe("0.00%");
  });

  it("formats score values with polarity prefix", () => {
    expect(fmtScore(0.45)).toBe("+0.45");
    expect(fmtScore(-0.75)).toBe("−0.75");
    expect(fmtScore(0)).toBe("0.00");
  });

  it("formats NPR currency in standard and compact forms (Lakh, Crore, Arab)", () => {
    expect(fmtNpr(50000)).toContain("Rs.");
    expect(fmtNpr(50000)).toContain("50,000");

    // Compact Lakh
    expect(fmtNpr(250000, true)).toBe("Rs. 2.50 Lakh");

    // Compact Crore
    expect(fmtNpr(15000000, true)).toBe("Rs. 1.50 Cr");

    // Compact Arab
    expect(fmtNpr(2000000000, true)).toBe("Rs. 2.00 Arab");
  });

  it("formats trading volumes in compact format", () => {
    expect(fmtVolume(850)).toBe("850");
    expect(fmtVolume(12500)).toBe("12.5K");
    expect(fmtVolume(1500000)).toBe("1.5M");
  });

  it("formats ISO dates nicely", () => {
    const formatted = fmtDate("2026-03-15");
    expect(formatted).toMatch(/15.*Mar.*2026/);
  });
});
