export function mm(value: number | null | undefined, digits = 1): string {
  return value == null || !Number.isFinite(value) ? "Unavailable" : `${value.toFixed(digits)} mm`;
}

export function score(value: number | null | undefined, digits = 3): string {
  return value == null || !Number.isFinite(value) ? "Undefined" : value.toFixed(digits);
}

export function percent(value: number | null | undefined, digits = 1): string {
  return value == null || !Number.isFinite(value) ? "Unavailable" : `${(value * 100).toFixed(digits)}%`;
}

export function utc(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    timeZone: "UTC", hour12: false,
  }).format(date) + " UTC";
}

export function regimeName(value: string): string {
  return ({ ACTIVE_MONSOON: "Active Monsoon", BREAK_WEAK_MONSOON: "Break / Weak Monsoon",
    LOW_DEPRESSION_INFLUENCED: "Low / Depression Influenced" } as Record<string, string>)[value] ?? value;
}

export function leadName(hours: number): string {
  return `Day ${Math.round(hours / 24)}`;
}
