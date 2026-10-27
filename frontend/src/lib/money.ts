// Parse decimal strings into integer minor units. Floating point is only used for display.
export function parseMinor(value: string, digits: number): number | null {
  if (value.length > 20 || !/^\d+(?:\.\d+)?$/.test(value)) return null;
  const [whole, fraction = ""] = value.split(".");
  if (fraction.length > digits) return null;
  const minor = Number(whole + fraction.padEnd(digits, "0"));
  return Number.isSafeInteger(minor) && minor <= 1_000_000_000_000
    ? minor
    : null;
}
export function amountInput(minor: number, digits: number): string {
  if (!digits) return String(minor);
  const text = String(minor).padStart(digits + 1, "0");
  return `${text.slice(0, -digits)}.${text.slice(-digits)}`;
}
export function money(minor: number, currency: string, digits: number): string {
  return new Intl.NumberFormat("zh-TW", {
    style: "currency",
    currency,
    currencyDisplay: "code",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(minor / 10 ** digits);
}
export function localToday(timezone: string): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((part) => part.type === type)?.value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}
