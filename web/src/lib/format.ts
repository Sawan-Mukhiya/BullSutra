/**
 * Financial and Date formatting helpers following Nepal conventions (NPR, lakh/crore, NPT)
 */

export function fmtPct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function fmtSignedPct(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const sign = x > 0 ? "+" : x < 0 ? "−" : "";
  const abs = Math.abs(x).toFixed(digits);
  return `${sign}${abs}%`;
}

export function fmtNum(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return x.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtScore(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const sign = x > 0 ? "+" : x < 0 ? "−" : "";
  return `${sign}${Math.abs(x).toFixed(2)}`;
}

export function fmtNpr(x: number | null | undefined, compact = false): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const abs = Math.abs(x);

  if (compact) {
    if (abs >= 10_000_000_00) { // 1 Arab = 100 Crore
      return `Rs. ${(x / 1_000_000_000).toFixed(2)} Arab`;
    }
    if (abs >= 10_000_000) { // 1 Crore = 100 Lakh
      return `Rs. ${(x / 10_000_000).toFixed(2)} Cr`;
    }
    if (abs >= 100_000) { // 1 Lakh
      return `Rs. ${(x / 100_000).toFixed(2)} Lakh`;
    }
  }

  const formatted = x.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
  return `Rs. ${formatted}`;
}

export function fmtVolume(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const abs = Math.abs(x);
  if (abs >= 1_000_000) return `${(x / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(x / 1_000).toFixed(1)}K`;
  return x.toString();
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return (
    d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Kathmandu",
    }) + " NPT"
  );
}

export function fmtRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const diffMs = Date.now() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return "Just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
