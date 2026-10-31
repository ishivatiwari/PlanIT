export const currencies = ["INR", "USD", "EUR", "GBP", "JPY"] as const;
export type Currency = (typeof currencies)[number];
const precision = (currency: Currency) => (currency === "JPY" ? 0 : 2);

export function parseMinor(value: string, currency: Currency): number | null {
  if (!value.trim()) return null;
  const digits = precision(currency);
  const pattern = digits === 0 ? /^\d+$/ : /^\d+(\.\d{1,2})?$/;
  if (!pattern.test(value.trim()))
    throw new Error(
      digits === 0
        ? "Enter a whole amount for JPY."
        : "Enter an amount with at most two decimal places, without commas.",
    );
  const [whole, fraction = ""] = value.trim().split(".");
  const result =
    BigInt(whole) * 10n ** BigInt(digits) +
    BigInt(fraction.padEnd(digits, "0") || "0");
  if (result > 9007199254740991n)
    throw new Error("The amount exceeds the supported range.");
  return Number(result);
}

export function minorInput(amount: number | null, currency: Currency): string {
  if (amount === null) return "";
  const digits = precision(currency),
    scale = 10n ** BigInt(digits),
    value = BigInt(amount);
  return `${value / scale}${digits ? "." + (value % scale).toString().padStart(digits, "0") : ""}`;
}

export function formatMoney(amount: number | null, currency: Currency): string {
  if (amount === null) return "Not set";
  const [whole, fraction] = minorInput(amount, currency).split(".");
  return `${currency} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(BigInt(whole))}${fraction === undefined ? "" : "." + fraction}`;
}
